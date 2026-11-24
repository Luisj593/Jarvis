"""Read-only project queries, independent of language model providers."""
import os, json, re, unicodedata
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

def normalize(s):
    return ''.join(c for c in unicodedata.normalize('NFD',s.lower()) if unicodedata.category(c)!='Mn')

def query(message, selected=""):
    allowed={"plazado":"Luisj593/Plazado","jarvis":"Luisj593/Jarvis","nightgest":None,"nightgest pruebas":None,"sv personalizado":None,"serviciopro":None,"plazado pruebas":None}
    aliases={"nightgest erp testing":"nightgest pruebas","nightgest erp":"nightgest","centros nocturnos":"nightgest","sv-personalizado":"sv personalizado","plazado - pruebas":"plazado pruebas","jarvis-ai":"jarvis"}

    msg=normalize(message)
    for alias,target in aliases.items():msg=msg.replace(alias,target)
    matches=[k for k in allowed if re.search(r"\b"+k+r"\b",msg)]
    matches=[k for k in matches if not any(k!=other and k in other for other in matches)]
    if any(x in msg for x in ("evalua","evaluacion","audita","auditoria","informe","diagnostico","que debemos corregir")):
        from project_evaluation import evaluate
        return evaluate(matches or ([normalize(selected)] if selected and "proyectos" not in msg and "todos" not in msg else []))
    if len(matches)>1:return {"text":"¿Cuál proyecto deseas consultar?","project":""}
    project=matches[0] if matches else normalize(selected)
    if "proyectos" in msg and any(x in msg for x in ("lista","cuales","tengo","muestra")):
        return {"text":"Proyectos registrados: Plazado, Jarvis, NightGest, NightGest pruebas, SV Personalizado, ServicioPro y Plazado pruebas.","project":project}
    if project not in allowed:return {"text":"¿Qué proyecto deseas consultar? Puedes decir Plazado, Jarvis, NightGest, SV Personalizado o ServicioPro.","project":""}
    if any(x in msg for x in ("desplieg","railway","produccion")):
        from railway_queries import status
        return {"text":status(project),"project":project,"source":"Railway"}
    if not any(x in msg for x in ("estado","error","fall","compil","prueba","avance","commit","cambio","revision")):
        return {"text":"Proyecto "+project+" seleccionado. Puedo consultar compilaciones y últimos cambios de GitHub.","project":project}
    if not allowed[project]:return {"text":"Este proyecto está registrado, pero su repositorio GitHub todavía no está vinculado.","project":project}
    token=(os.getenv("JARVIS_GITHUB_READ_TOKEN") or os.getenv("JARVIS_MONITOR_GITHUB_TOKEN",""))
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
