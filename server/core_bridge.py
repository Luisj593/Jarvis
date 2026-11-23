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
    except (ValueError,TypeError) :
        return 400,{"error":"invalid_parameters"}
    except PermissionError:
        return 403,{"error":"forbidden"}
    except KeyError:
        return 404,{"error":"not_found"}
    except ProjectConflict:
        return 409,{"error":"version_conflict"}
