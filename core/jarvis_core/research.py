"""JARVIS Research: fuentes RSS confiables, reglas deterministas y tareas opt-in.

No usa LLM. No navega URLs arbitrarias, no ejecuta acciones y no guarda
investigaciones como enseñanzas implícitas.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.request import build_opener, HTTPSHandler, HTTPRedirectHandler, Request
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET
from uuid import uuid4
import re
from .storage import SQLiteMemoryStore
from .security import Principal, require_permission

SOURCES={
    "tecnologia": ("BBC Tecnología", "https://feeds.bbci.co.uk/mundo/temas/tecnologia/rss.xml"),
    "mundo": ("BBC Mundo", "https://feeds.bbci.co.uk/mundo/rss.xml"),
}
MAX_BYTES=512_000
MAX_ITEMS=12
MIN_INTERVAL=60
class ResearchError(Exception): pass
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): raise ResearchError("redirección bloqueada")

@dataclass(frozen=True)
class Finding:
    title:str
    link:str
    published:str
    source:str

@dataclass(frozen=True)
class ResearchResult:
    topic:str
    summary:str
    findings:tuple[Finding,...]
    checked_at:str

class Research:
    def __init__(self,path,principal:Principal,fetch=None):
        self.principal=principal
        self.store=SQLiteMemoryStore(path,principal.owner_id)
        self.fetch=fetch or self._fetch
        with self.store._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS research_jobs(
                id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, topic TEXT NOT NULL,
                source_key TEXT NOT NULL, interval_minutes INTEGER NOT NULL,
                enabled INTEGER NOT NULL, next_due TEXT NOT NULL,
                last_run TEXT, CHECK(interval_minutes>=60))""")
            db.execute("CREATE INDEX IF NOT EXISTS research_due_idx ON research_jobs(owner_id,enabled,next_due)")
            db.execute("""CREATE TABLE IF NOT EXISTS research_history(
                id TEXT PRIMARY KEY,owner_id TEXT NOT NULL,job_id TEXT,
                topic TEXT NOT NULL,source_key TEXT NOT NULL,
                summary TEXT NOT NULL,checked_at TEXT NOT NULL)""")
    @staticmethod
    def _validate(topic,source_key):
        if not isinstance(topic,str) or not topic.strip() or len(topic)>120:
            raise ValueError("tema inválido")
        if source_key not in SOURCES: raise ValueError("fuente no autorizada")
    @staticmethod
    def _fetch(url):
        # Solo endpoints definidos en código; sin URL proporcionada por usuario.
        if url not in (x[1] for x in SOURCES.values()): raise ResearchError("fuente no autorizada")
        if urlsplit(url).scheme!="https": raise ResearchError("HTTPS requerido")
        opener=build_opener(HTTPSHandler(),NoRedirect())
        with opener.open(Request(url,headers={"User-Agent":"JarvisResearch/1.0","Accept":"application/rss+xml,application/xml"}),timeout=8) as response:
            if response.status!=200: raise ResearchError("fuente no disponible")
            data=response.read(MAX_BYTES+1)
            if len(data)>MAX_BYTES: raise ResearchError("respuesta demasiado grande")
            return data
    def investigate(self,topic,source_key="tecnologia"):
        require_permission(self.principal,"memory:read")
        self._validate(topic,source_key)
        source,url=SOURCES[source_key]
        try: root=ET.fromstring(self.fetch(url))
        except ET.ParseError as exc: raise ResearchError("RSS inválido") from exc
        tokens=set(re.findall(r"\w+",topic.casefold()))-{"de","la","el","en","y","sobre","los","las"}
        findings=[]
        for item in root.findall(".//item")[:100]:
            title=(item.findtext("title") or "").strip()[:240]
            link=(item.findtext("link") or "").strip()
            published=(item.findtext("pubDate") or "").strip()[:90]
            if not title or not link.startswith("https://"):continue
            if tokens and not any(token in title.casefold() for token in tokens):continue
            findings.append(Finding(title,link,published,source))
            if len(findings)>=MAX_ITEMS:break
        summary=(f"Encontré {len(findings)} titulares relacionados con {topic.strip()} en {source}. "
                 "Son titulares extraídos de RSS, no una verificación independiente del contenido."
                 if findings else f"No encontré titulares coincidentes para {topic.strip()} en {source}.")
        return ResearchResult(topic.strip(),summary,tuple(findings),datetime.now(timezone.utc).isoformat())
    def schedule(self,topic,source_key="tecnologia",interval_minutes=1440):
        require_permission(self.principal,"memory:write")
        self._validate(topic,source_key)
        if type(interval_minutes) is not int or not MIN_INTERVAL<=interval_minutes<=43200:
            raise ValueError("intervalo inválido")
        job_id=str(uuid4())
        due=(datetime.now(timezone.utc)+timedelta(minutes=interval_minutes)).isoformat()
        with self.store._connect() as db:
            db.execute("INSERT INTO research_jobs VALUES(?,?,?,?,?,?,?,NULL)",
                (job_id,self.principal.owner_id,topic.strip(),source_key,interval_minutes,1,due))
        return job_id
    def cancel(self,job_id):
        require_permission(self.principal,"memory:write")
        with self.store._connect() as db:
            return db.execute("UPDATE research_jobs SET enabled=0 WHERE owner_id=? AND id=?",
                              (self.principal.owner_id,job_id)).rowcount==1
    def jobs(self):
        require_permission(self.principal,"memory:read")
        with self.store._connect() as db:
            return db.execute("SELECT id,topic,source_key,interval_minutes,enabled,next_due FROM research_jobs WHERE owner_id=? ORDER BY next_due",
                              (self.principal.owner_id,)).fetchall()
    def run_due(self,now=None,limit=3):
        """Invocado por un planificador confiable; no se ejecuta automáticamente."""
        require_permission(self.principal,"memory:read")
        require_permission(self.principal,"memory:write")
        if type(limit) is not int or not 1<=limit<=10:raise ValueError("límite inválido")
        now=now or datetime.now(timezone.utc)
        if now.tzinfo is None:raise ValueError("fecha debe incluir zona")
        stamp=now.astimezone(timezone.utc).isoformat()
        with self.store._connect() as db:
            rows=db.execute("""SELECT id,topic,source_key,interval_minutes FROM research_jobs
                WHERE owner_id=? AND enabled=1 AND next_due<=? ORDER BY next_due LIMIT ?""",
                (self.principal.owner_id,stamp,limit)).fetchall()
        results=[]
        for job_id,topic,source_key,interval in rows:
            # Reserva atómica antes de la red para evitar ejecuciones duplicadas.
            next_due=(now+timedelta(minutes=interval)).astimezone(timezone.utc).isoformat()
            with self.store._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                changed=db.execute("""UPDATE research_jobs SET next_due=? WHERE
                    id=? AND owner_id=? AND enabled=1 AND next_due<=?""",
                    (next_due,job_id,self.principal.owner_id,stamp)).rowcount
            if not changed:continue
            try: result=self.investigate(topic,source_key)
            except (ResearchError,OSError,TimeoutError):
                continue  # Reintento en el siguiente intervalo; sin bucle agresivo.
            with self.store._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                db.execute("UPDATE research_jobs SET last_run=? WHERE id=? AND owner_id=?",
                           (stamp,job_id,self.principal.owner_id))
                db.execute("INSERT INTO research_history VALUES(?,?,?,?,?,?,?)",
                           (str(uuid4()),self.principal.owner_id,job_id,topic,source_key,result.summary,result.checked_at))
            results.append((job_id,result))
        return results
    def history(self,limit=50):
        require_permission(self.principal,"memory:read")
        if type(limit) is not int or not 1<=limit<=100:raise ValueError("límite inválido")
        with self.store._connect() as db:
            return db.execute("""SELECT job_id,topic,source_key,summary,checked_at
                FROM research_history WHERE owner_id=? ORDER BY checked_at DESC LIMIT ?""",
                (self.principal.owner_id,limit)).fetchall()
