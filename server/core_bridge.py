"""Puente HTTP limitado para el núcleo determinista de JARVIS.

Requiere que server.app autentique Bearer antes de llamar a dispatch.
No recibe owner_id ni permisos desde el cuerpo de la petición.
"""
from dataclasses import asdict
import os
from jarvis_core.security import Principal
from jarvis_core.projects import ProjectRegistry, ProjectConflict
from jarvis_core.responses import ResponseComposer
from jarvis_core.audit import AuditedActions
from jarvis_core.research import Research,ResearchError
from project_monitor import inventory as project_inventory,report as project_report
from jarvis_core.implementation import ImplementationEngine,ExecutionConflict

PERMISSIONS=frozenset({"memory:read","memory:write","action:execute"})

def _services():
    owner=os.environ.get("JARVIS_OWNER_ID","").strip()
    if not owner:
        raise RuntimeError("JARVIS_OWNER_ID no configurado")
    path=os.environ.get("JARVIS_DB_PATH","/tmp/jarvis.sqlite")
    principal=Principal(owner,PERMISSIONS)
    return ProjectRegistry(path,principal),ResponseComposer(path,principal),AuditedActions(path,principal,strict_policies=True)

def dispatch(method,path,data=None):
    """Retorna (status, JSON); no realiza ninguna acción externa."""
    projects,responses,actions=_services()
    data=data or {}
    try:
        if path.startswith("/v1/core/implementation/"):
            engine=ImplementationEngine(os.environ.get("JARVIS_DB_PATH","/tmp/jarvis.sqlite"),
                                        Principal(os.environ["JARVIS_OWNER_ID"],PERMISSIONS))
            if method=="GET" and path=="/v1/core/implementation/runs":
                return 200,{"runs":engine.list()}
            if method=="POST" and path=="/v1/core/implementation/create":
                if set(data)!={"project_id","request"}:return 400,{"error":"invalid_parameters"}
                return 201,{"run":engine.create(data["project_id"],data["request"])}
            if method=="POST" and path=="/v1/core/implementation/advance":
                if set(data)!={"run_id","stage","evidence","passed","gate"}:
                    return 400,{"error":"invalid_parameters"}
                return 200,{"run":engine.advance(**data)}
            return 404,{"error":"not_found"}
        if method=="GET" and path=="/v1/core/monitor/catalog":
            return 200,project_inventory()
        if method=="GET" and path=="/v1/core/monitor/report":
            return 200,project_report()
        if path.startswith("/v1/core/research/"):
            research=Research(os.environ.get("JARVIS_DB_PATH","/tmp/jarvis.sqlite"),
                              Principal(os.environ["JARVIS_OWNER_ID"],PERMISSIONS))
            if method=="GET" and path=="/v1/core/research/jobs":
                return 200,{"jobs":[{"id":r[0],"topic":r[1],"source":r[2],
                    "interval_minutes":r[3],"enabled":bool(r[4]),"next_due":r[5]} for r in research.jobs()]}
            if method=="GET" and path=="/v1/core/research/history":
                return 200,{"history":[{"job_id":r[0],"topic":r[1],"source":r[2],
                    "summary":r[3],"checked_at":r[4]} for r in research.history()]}
            if method=="POST" and path=="/v1/core/research/query":
                if set(data)!={"topic","source"}:return 400,{"error":"invalid_parameters"}
                result=research.investigate(data["topic"],data["source"])
                return 200,{"result":asdict(result)}
            if method=="POST" and path=="/v1/core/research/schedule":
                if set(data)!={"topic","source","interval_minutes"}:return 400,{"error":"invalid_parameters"}
                job_id=research.schedule(data["topic"],data["source"],data["interval_minutes"])
                return 201,{"job_id":job_id,"execution":"requires_scheduler"}
            if method=="POST" and path=="/v1/core/research/cancel":
                if set(data)!={"job_id"}:return 400,{"error":"invalid_parameters"}
                return 200,{"cancelled":research.cancel(data["job_id"])}
            return 404,{"error":"not_found"}
        if method=="GET" and path=="/v1/core/projects":
            return 200,{"projects":[asdict(p) for p in projects.list()]}
        if method=="GET" and path=="/v1/core/actions":
            return 200,{"allowed":list(actions.actions.catalog()),"strict_policies":True}
        if method=="GET" and path=="/v1/core/audit":
            return 200,{"integrity":actions.verify_integrity(),"events":[asdict(e) for e in actions.history()[-100:]]}
        if method=="POST" and path=="/v1/core/projects":
            if set(data)!={"name","objective"}:
                return 400,{"error":"invalid_parameters"}
            return 201,{"project":asdict(projects.create(data["name"],data["objective"]))}
        if method=="POST" and path=="/v1/core/conversation/select":
            if set(data)!={"session_id","project"}:
                return 400,{"error":"invalid_parameters"}
            responses.conversation.select_project(data["session_id"],data["project"])
            return 200,{"selected":True}
        if method=="POST" and path=="/v1/core/conversation/respond":
            if set(data)!={"session_id","message"}:
                return 400,{"error":"invalid_parameters"}
            return 200,{"response":asdict(responses.respond(data["session_id"],data["message"]))}
        if method=="POST" and path=="/v1/core/actions/preview":
            if set(data)!={"project_id","action","params"}:
                return 400,{"error":"invalid_parameters"}
            preview=actions.preview(data["action"],data["project_id"],data["params"])
            return 200,{"preview":asdict(preview)}
        if method=="POST" and path=="/v1/core/actions/confirm":
            if set(data)!={"ticket","confirmation"}:
                return 400,{"error":"invalid_parameters"}
            return 200,{"result":asdict(actions.confirm(data["ticket"],data["confirmation"]))}
        if method=="POST" and path=="/v1/core/actions/policy":
            if set(data)!={"project_id","allowed","expected_version"}:
                return 400,{"error":"invalid_parameters"}
            version=actions.set_project_permission(data["project_id"],data["allowed"],data["expected_version"])
            return 200,{"policy_version":version}
        return 404,{"error":"not_found"}
    except ResearchError:
        return 502,{"error":"research_source_unavailable"}
    except (ValueError,TypeError) :
        return 400,{"error":"invalid_parameters"}
    except PermissionError:
        return 403,{"error":"forbidden"}
    except KeyError:
        return 404,{"error":"not_found"}
    except (ProjectConflict,ExecutionConflict):
        return 409,{"error":"version_conflict"}
