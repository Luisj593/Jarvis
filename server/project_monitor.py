"""Observabilidad de proyectos: GET/GraphQL de solo lectura, sin mutaciones.

Si no hay credenciales de monitorización, muestra inventario verificado y
estado 'unknown', nunca presume que un servicio está sano.
"""
import json
import os
import urllib.request
import urllib.error
from datetime import datetime,timezone
from pathlib import Path

INVENTORY=Path(__file__).with_name("project_inventory.json")
MAX_RESPONSE=1_000_000
GITHUB_API="https://api.github.com"
RAILWAY_API="https://backboard.railway.com/graphql/v2"

def _request(url,token,method="GET",payload=None):
    if url!=RAILWAY_API and not url.startswith(GITHUB_API+"/"):
        raise ValueError("host no permitido")
    if method not in ("GET","POST") or (method=="POST" and url!=RAILWAY_API):
        raise ValueError("método no permitido")
    headers={"Accept":"application/json","Authorization":("Bearer " if url==RAILWAY_API else "Bearer ")+token,
             "User-Agent":"JARVIS-Observability/1.0"}
    body=json.dumps(payload).encode() if payload is not None else None
    if body is not None:headers["Content-Type"]="application/json"
    req=urllib.request.Request(url,data=body,headers=headers,method=method)
    opener=urllib.request.build_opener(_NoRedirect())
    with opener.open(req,timeout=8) as resp:
        raw=resp.read(MAX_RESPONSE+1)
        if len(raw)>MAX_RESPONSE:raise ValueError("respuesta demasiado grande")
        return json.loads(raw)

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError("redirección bloqueada")

def inventory():
    with INVENTORY.open(encoding="utf-8") as f:return json.load(f)

def report(fetch=_request):
    inv=inventory()
    result={"checked_at":datetime.now(timezone.utc).isoformat(),
            "snapshot_date":inv["discovered_at"],"mode":"read_only",
            "github":[],"railway":[],"warnings":[]}
    gh=os.environ.get("JARVIS_MONITOR_GITHUB_TOKEN","")
    rw=os.environ.get("JARVIS_MONITOR_RAILWAY_TOKEN","")
    result["alerts"]=[]
    for name in inv["github"]:
        item={"repository":name,"status":"unknown","open_issues":None,
              "last_workflow":None,"error":None}
        if not gh:item["error"]="monitor_token_not_configured"
        else:
            try:
                repo=fetch(GITHUB_API+"/repos/"+name,gh)
                item["status"]="archived" if repo.get("archived") else "accessible"
                item["open_issues"]=repo.get("open_issues_count")
                try:
                    runs=fetch(GITHUB_API+"/repos/"+name+"/actions/runs?per_page=1",gh)
                except urllib.error.HTTPError as exc:
                    item["error"]="github_actions_http_"+str(exc.code)
                    runs={}
                latest=(runs.get("workflow_runs") or [None])[0]
                if latest:
                    item["last_workflow"]={"name":latest.get("name"),"status":latest.get("status"),
                       "conclusion":latest.get("conclusion"),"url":latest.get("html_url")}
                    if latest.get("conclusion") in ("failure","timed_out","cancelled","action_required"):
                        result["alerts"].append({"provider":"github","project":name,
                            "kind":"workflow_problem","severity":"warning",
                            "detail":latest.get("conclusion"),"url":latest.get("html_url")})
            except urllib.error.HTTPError as exc:
                item["error"]="github_http_"+str(exc.code)
            except (urllib.error.URLError,ValueError,KeyError,TimeoutError):
                item["error"]="github_unavailable"
        result["github"].append(item)
    for project in inv["railway"]:
        item={"project":project["name"],"project_id":project["id"],"status":"unknown",
              "services":[],"error":None}
        if not rw:item["error"]="monitor_token_not_configured"
        else:
            # IDs son del inventario controlado; variables GraphQL, sin interpolación.
            query="""query JarvisProjectRead($id: String!) {
              project(id: $id) {
                id name
                services { edges { node { id name } } }
                environments { edges { node { id name } } }
              }
            }"""
            try:
                payload=fetch(RAILWAY_API,rw,"POST",{"query":query,"variables":{"id":project["id"]}})
                if payload.get("errors"):raise ValueError("Railway GraphQL error")
                node=(payload.get("data") or {}).get("project")
                if node is None:raise ValueError("project unavailable")
                item["status"]="accessible"
                item["services"]=[{"id":edge["node"]["id"],"name":edge["node"]["name"],
                    "status":"unknown"} for edge in node.get("services",{}).get("edges",[])][:100]
                item["environments"]=[edge["node"]["name"] for edge in
                    node.get("environments",{}).get("edges",[])][:30]
                # Consultar despliegues por servicio/entorno sin alterar el proyecto.
                deployments_query="""query JarvisDeployments($input: DeploymentListInput!) {
                  deployments(first: 1, input: $input) {
                    edges { node { id status createdAt } }
                  }
                }"""
                for service in item["services"]:
                    service["deployments"]=[]
                    for env in node.get("environments",{}).get("edges",[])[:10]:
                        env_node=env["node"]
                        try:
                            dep=fetch(RAILWAY_API,rw,"POST",{"query":deployments_query,
                                "variables":{"input":{"projectId":project["id"],
                                    "serviceId":service["id"],"environmentId":env_node["id"]}}})
                            if dep.get("errors"):
                                service["deployments"].append({"environment":env_node["name"],"status":"unknown","error":"deployment_query_unavailable"})
                                continue
                            edges=((dep.get("data") or {}).get("deployments") or {}).get("edges") or []
                            latest=edges[0]["node"] if edges else None
                            state=latest.get("status","unknown") if latest else "no_deployments"
                            service["deployments"].append({"environment":env_node["name"],"status":state})
                            if state in ("FAILED","CRASHED"):
                                result["alerts"].append({"provider":"railway","project":project["name"],
                                    "service":service["name"],"environment":env_node["name"],
                                    "kind":"deployment_failure","severity":"warning","detail":state})
                        except (urllib.error.HTTPError,urllib.error.URLError,ValueError,KeyError,TypeError,TimeoutError):
                            service["deployments"].append({"environment":env_node["name"],"status":"unknown","error":"deployment_query_unavailable"})
            except (urllib.error.URLError,ValueError,KeyError,TypeError,TimeoutError):
                item["error"]="railway_unavailable"
        result["railway"].append(item)
    if not gh:result["warnings"].append("GitHub live monitoring requires a read-only token")
    if not rw:result["warnings"].append("Railway live monitoring requires a read-only token")
    result["summary"]={"alerts":len(result["alerts"]),"github_repositories":len(result["github"]),
                       "railway_projects":len(result["railway"]),
                       "github_errors":sum(bool(x["error"]) for x in result["github"]),
                       "railway_errors":sum(bool(x["error"]) for x in result["railway"])}
    return result
