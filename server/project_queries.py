"""Read-only project queries, independent of language model providers."""
import os, json, re, unicodedata
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

def normalize(s):
    return ''.join(c for c in unicodedata.normalize('NFD',s.lower()) if unicodedata.category(c)!='Mn')

def query(message, selected=""):
    allowed={"plazado":"Luisj593/Plazado","jarvis":"Luisj593/Jarvis"}
    msg=normalize(message)
    matches=[k for k in allowed if re.search(r"\b"+k+r"\b",msg)]
    if len(matches)>1:return {"text":"¿Cuál proyecto deseas consultar?","project":""}
    project=matches[0] if matches else normalize(selected)
    if "proyectos" in msg and any(x in msg for x in ("lista","cuales","tengo","muestra")):
        return {"text":"Proyectos disponibles para consulta: Plazado y Jarvis.","project":project}
    if project not in allowed:return {"text":"¿Quieres consultar Plazado o Jarvis?","project":""}
    if any(x in msg for x in ("desplieg","railway","produccion")):
        return {"text":"La consulta directa de Railway todavía no está habilitada. No puedo confirmar el despliegue.","project":project}
    if not any(x in msg for x in ("estado","error","fall","compil","prueba","avance","commit","cambio","revision")):
        return {"text":"Proyecto "+project+" seleccionado. Puedo consultar compilaciones y últimos cambios de GitHub.","project":project}
    token=os.getenv("JARVIS_GITHUB_READ_TOKEN","")
    if not token:return {"text":"Falta configurar el acceso de lectura a GitHub en el servidor.","project":project}
    endpoint="actions/runs?per_page=5" if any(x in msg for x in ("estado","error","fall","compil","prueba","avance")) else "commits?per_page=1"
    req=Request("https://api.github.com/repos/"+allowed[project]+"/"+endpoint,headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json","User-Agent":"Jarvis-project-reader"})
    try:
        with urlopen(req,timeout=8) as response:data=json.load(response)
    except (HTTPError,URLError,TimeoutError,ValueError):
        return {"text":"No pude consultar GitHub. Revisa los permisos y la conexión.","project":project}
    if endpoint.startswith("actions"):
        runs=data.get("workflow_runs",[])
        answer="; ".join(str(r.get("name"))+" en "+str(r.get("head_branch"))+": "+str(r.get("conclusion") or r.get("status")) for r in runs[:3]) or "No hay ejecuciones disponibles."
    else:
        answer=("Último cambio: "+data[0]["commit"]["message"][:300]) if data else "No hay cambios disponibles."
    return {"text":answer,"project":project,"source":"GitHub"}
