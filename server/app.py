import json, os, hmac, sqlite3, threading, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

DB=os.environ.get("JARVIS_DB_PATH","/tmp/jarvis.sqlite")
TOKEN=os.environ.get("JARVIS_API_TOKEN","")
lock=threading.Lock()
with sqlite3.connect(DB) as conn:
    conn.execute("CREATE TABLE IF NOT EXISTS lessons (id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")

class Handler(BaseHTTPRequestHandler):
    def send(self,status,data):
        body=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Cache-Control","no-store")
        self.send_header("Content-Length",str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def authorized(self):
        header=self.headers.get("Authorization","")
        return bool(TOKEN) and hmac.compare_digest(header,"Bearer "+TOKEN)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=="/health":
            return self.send(200,{"status":"ok","service":"jarvis-brain","version":"0.1","ready":bool(TOKEN)})
        if not self.authorized(): return self.send(401,{"error":"unauthorized"})
        if path=="/projects":
            return self.send(200,{"projects":[{"name":name,"access":"catalog-only"} for name in ["Plazado","NightGest-ERP","NightGest-ERP-Testing","SV-Personalizado","ServicioPro","Plazado - Pruebas"]]})
        if path=="/lessons":
            with lock, sqlite3.connect(DB) as conn:
                rows=conn.execute("SELECT id,project,content,created_at FROM lessons ORDER BY id DESC LIMIT 200").fetchall()
            return self.send(200,{"lessons":[dict(zip(["id","project","content","created_at"],r)) for r in rows]})
        self.send(404,{"error":"not_found"})
    def do_POST(self):
        if not self.authorized(): return self.send(401,{"error":"unauthorized"})
        path=urlparse(self.path).path
        if path not in ("/lessons","/chat"): return self.send(404,{"error":"not_found"})
        try:
            length=int(self.headers.get("Content-Length","0"))
            if length<=0 or length>8192:return self.send(413,{"error":"invalid_size"})
            obj=json.loads(self.rfile.read(length))
            if path=="/chat":
                message=obj.get("message","")
                project=obj.get("project","general")
                if not isinstance(message,str) or not message.strip() or len(message)>3000 or not isinstance(project,str) or len(project)>100:
                    return self.send(400,{"error":"invalid_chat"})
                normalized=message.lower().strip()
                with lock, sqlite3.connect(DB) as conn:
                    lessons=conn.execute("SELECT content FROM lessons WHERE project IN (?, 'general') ORDER BY id DESC LIMIT 100",(project,)).fetchall()
                if normalized.startswith(("aprende:","recuerda:","cuando diga ")):
                    with lock, sqlite3.connect(DB) as conn:
                        conn.execute("INSERT INTO lessons(project,content) VALUES (?,?)",(project,message.strip()))
                    return self.send(200,{"reply":"He guardado esa enseñanza. Puedes consultarla o corregirla.","learned":True})
                if "qué recuerdas" in normalized or "que recuerdas" in normalized:
                    return self.send(200,{"reply":"Recuerdo: "+("; ".join(row[0] for row in lessons[:8]) if lessons else "todavía no me has enseñado nada."),"learned":False})
                matched=[row[0] for row in lessons if normalized in row[0].lower() or row[0].lower() in normalized]
                if matched:
                    return self.send(200,{"reply":"Según lo que me enseñaste: "+matched[0],"learned":False})
                return self.send(200,{"reply":"Te escucho. Todavía no tengo una regla para eso. Puedes enseñármela diciendo aprende: seguido de la instrucción.","learned":False})
            project=obj.get("project","general")
            content=obj.get("content","")
            if not isinstance(project,str) or not isinstance(content,str) or not project.strip() or not content.strip() or len(project)>100 or len(content)>3000:
                return self.send(400,{"error":"invalid_lesson"})
            with lock, sqlite3.connect(DB) as conn:
                cur=conn.execute("INSERT INTO lessons(project,content) VALUES (?,?)",(project.strip(),content.strip()))
                lesson_id=cur.lastrowid
            return self.send(201,{"id":lesson_id,"stored":True})
        except (ValueError,TypeError,json.JSONDecodeError):
            return self.send(400,{"error":"invalid_json"})
    def log_message(self,format,*args): pass

ThreadingHTTPServer(("0.0.0.0",int(os.environ.get("PORT","8080"))),Handler).serve_forever()
