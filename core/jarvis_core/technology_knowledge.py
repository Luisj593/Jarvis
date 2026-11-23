"""Investigación tecnológica persistente, limitada a RSS autorizados.
Los hallazgos son referencias externas, nunca instrucciones para el asistente.
"""
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from datetime import datetime, timezone
from xml.etree import ElementTree as ET
from .research import Research, ResearchError, SOURCES

TOPICS={
 "comercio_electronico":("tienda","online","comercio","electrónico","ecommerce","marketplace","venta","compra","retail","shopping","amazon","temu"),
 "pagos":("pago","tarjeta","fintech","banco","fraude","paypal","stripe"),
 "logistica":("envío","entrega","logística","courier","almacén","inventario","delivery"),
 "inteligencia_artificial":("inteligencia artificial","ia","ai","modelo","automatización"),
 "ciberseguridad":("seguridad","ciber","hack","privacidad","ransomware"),
 "desarrollo":("software","programación","desarrollador","aplicación","android","web","nube","servidor"),
 "tecnologia_general":("tecnología","digital","internet","startup","innovación")
}
class TechnologyKnowledge:
 def __init__(self,path,principal):
  self.research=Research(path,principal)
  self.store=self.research.store
  self.owner=principal.owner_id
  with self.store._connect() as db:
   db.execute("""CREATE TABLE IF NOT EXISTS technology_knowledge(
    id TEXT PRIMARY KEY,owner_id TEXT NOT NULL,category TEXT NOT NULL,
    title TEXT NOT NULL,source TEXT NOT NULL,url TEXT NOT NULL,
    published TEXT,observed_at TEXT NOT NULL,review_status TEXT NOT NULL DEFAULT 'reference',
    UNIQUE(owner_id,url))""")
   db.execute("CREATE INDEX IF NOT EXISTS technology_knowledge_owner_idx ON technology_knowledge(owner_id,category)")
 def import_official_dgii(self):
  """Importa fichas curadas del repositorio; no convierte texto web en órdenes."""
  path=Path(__file__).resolve().parent/"data"/"dgii_facturacion_electronica_rd.json"
  payload=json.loads(path.read_text(encoding="utf-8"))
  inserted=0
  checked=datetime.now(timezone.utc).isoformat()
  with self.store._connect() as db:
   for record in payload["records"]:
    url=record["url"]
    if not url.startswith("https://") or "dgii.gov.do" not in url.split("/")[2]:
     raise ValueError("fuente DGII inválida")
    title=record["title"][:240]
    summary=record["summary"][:3000]
    identifier=hashlib.sha256((self.owner+"|"+url+"|"+title).encode()).hexdigest()
    db.execute("""CREATE TABLE IF NOT EXISTS knowledge_notes(
      id TEXT PRIMARY KEY,owner_id TEXT NOT NULL,category TEXT NOT NULL,
      title TEXT NOT NULL,summary TEXT NOT NULL,source TEXT NOT NULL,
      url TEXT NOT NULL,verified_on TEXT NOT NULL,created_at TEXT NOT NULL,
      UNIQUE(owner_id,category,title))""")
    result=db.execute("""INSERT OR IGNORE INTO knowledge_notes
      (id,owner_id,category,title,summary,source,url,verified_on,created_at)
      VALUES(?,?,?,?,?,?,?,?,?)""",(identifier,self.owner,"facturacion_electronica_rd",
       title,summary,"DGII",url,payload["verified_on"],checked))
    inserted+=result.rowcount
  return {"topic":payload["topic"],"new_notes":inserted,"total_sources":len(payload["records"])}
 def official_notes(self):
  self.import_official_dgii()
  with self.store._connect() as db:
   rows=db.execute("""SELECT title,summary,source,url,verified_on FROM knowledge_notes
    WHERE owner_id=? AND category='facturacion_electronica_rd' ORDER BY title""",(self.owner,)).fetchall()
  return [{"title":t,"summary":s,"source":src,"url":u,"verified_on":v} for t,s,src,u,v in rows]
 def collect(self):
  checked=datetime.now(timezone.utc).isoformat()
  found=0
  inserted=0
  failures=[]
  for key in ("tecnologia",):
   source,url=SOURCES[key]
   try:
    root=ET.fromstring(self.research.fetch(url))
    items=root.findall(".//item")[:100]
   except (ResearchError,OSError,TimeoutError,ET.ParseError) as exc:
    failures.append(source+": fuente no disponible")
    continue
   for item in items:
    title=(item.findtext("title") or "").strip()[:240]
    link=(item.findtext("link") or "").strip()[:800]
    published=(item.findtext("pubDate") or "").strip()[:90]
    if not title or not link.startswith("https://"):continue
    lower=title.casefold()
    matches=[category for category,terms in TOPICS.items() if any(t in lower for t in terms)]
    if not matches:continue
    category=matches[0]
    found+=1
    identifier=hashlib.sha256((self.owner+"|"+link).encode()).hexdigest()
    with self.store._connect() as db:
     result=db.execute("""INSERT OR IGNORE INTO technology_knowledge
       (id,owner_id,category,title,source,url,published,observed_at)
       VALUES(?,?,?,?,?,?,?,?)""",(identifier,self.owner,category,title,source,link,published,checked))
     inserted+=result.rowcount
  return {"checked_at":checked,"items_matched":found,"new_references":inserted,
   "source_errors":failures,"priority":"comercio_electronico",
   "note":"Referencias de titulares RSS, no contenido verificado ni aprendizaje de un modelo."}
 def list(self,limit=60):
  if type(limit) is not int or not 1<=limit<=100:raise ValueError("límite inválido")
  with self.store._connect() as db:
   rows=db.execute("""SELECT category,title,source,url,published,observed_at
    FROM technology_knowledge WHERE owner_id=?
    ORDER BY CASE WHEN category='comercio_electronico' THEN 0 ELSE 1 END,
    observed_at DESC LIMIT ?""",(self.owner,limit)).fetchall()
  return [{"category":a,"title":b,"source":c,"url":d,"published":e,"observed_at":f} for a,b,c,d,e,f in rows]
