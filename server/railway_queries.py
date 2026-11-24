"""Fixed read-only Railway GraphQL query. Never accepts arbitrary GraphQL."""
import os,json
from urllib.request import Request,urlopen
from urllib.error import URLError
PROJECTS={"jarvis":"8e9632bb-2d0f-430d-b1da-9977c7ed3c95","nightgest":"9234424d-85a2-4448-be24-2012cb042959","nightgest pruebas":"c939a170-31a8-463f-b3c0-0b089553ab56","sv personalizado":"ef7e2987-346b-4037-954a-bd908f4d2308","serviciopro":"d8d9f6dd-4a86-4044-ab23-6d04351d7185","plazado pruebas":"f3a02a6b-8f5d-4b93-b05d-f63b17c1b42b"}
QUERY="""query ProjectStatus($id: String!) { project(id: $id) { name environments { edges { node { name serviceInstances { edges { node { serviceName latestDeployment { status } } } } } } } } }"""
def status(project):
    pid=PROJECTS.get(project)
    if not pid:return "El proyecto de Railway todavía no está vinculado."
    token=(os.getenv("JARVIS_RAILWAY_READ_TOKEN") or os.getenv("JARVIS_MONITOR_RAILWAY_TOKEN",""))
    if not token:return "Falta configurar el acceso de lectura a Railway."
    req=Request("https://backboard.railway.com/graphql/v2",data=json.dumps({"query":QUERY,"variables":{"id":pid}}).encode(),headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"},method="POST")
    try:
        with urlopen(req,timeout=8) as response:result=json.load(response)
        if result.get("errors"):return "Railway no permitió consultar el estado. Revisa los permisos."
        p=result["data"]["project"]
        rows=[]
        for edge in p["environments"]["edges"]:
            env=edge["node"]
            for item in env["serviceInstances"]["edges"]:
                svc=item["node"]
                rows.append(env["name"]+", "+svc["serviceName"]+": "+str((svc.get("latestDeployment") or {}).get("status","sin despliegue")))
        return p["name"]+": "+("; ".join(rows[:12]) or "sin servicios disponibles")
    except (URLError,TimeoutError,ValueError,KeyError,TypeError):
        return "No pude consultar Railway en este momento."
