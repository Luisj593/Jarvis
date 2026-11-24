"""Deterministic technical evaluation, no language model calls."""
from project_monitor import report
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import threading
_pool=ThreadPoolExecutor(max_workers=1)
_lock=threading.Lock()
_pending=None

def evaluate(projects, fetch_report=None):
    global _pending
    if fetch_report is None:
        with _lock:
            if _pending is None or _pending.done():
                _pending=_pool.submit(report)
            future=_pending
        try:
            data=future.result(timeout=45)
        except TimeoutError:
            return {"text":"La evaluación sigue en curso. Solicita nuevamente el informe en unos momentos.","project":"","source":"GitHub y Railway"}
    else:
        data=fetch_report()
    def norm(value):
        return value.lower().replace("-"," ").replace(" erp","").replace(" testing"," pruebas").replace(" ai","").strip()
    def included(value):
        name=norm(value.split("/")[-1])
        return not projects or name in projects
    rows=[]
    alerts=[]
    for item in data.get("github",[]):
        if not included(item["repository"]):continue
        workflow=item.get("last_workflow") or {}
        rows.append(item["repository"]+": "+("consulta incompleta" if item.get("error") else str(workflow.get("conclusion") or workflow.get("status") or "sin pruebas registradas")))
    for item in data.get("railway",[]):
        if not included(item["project"]):continue
        states=[s["name"]+" "+d["environment"]+": "+d["status"] for s in item.get("services",[]) for d in s.get("deployments",[])]
        rows.append(item["project"]+": "+("; ".join(states) if states else "estado no confirmado"))
    for alert in data.get("alerts",[]):
        if included(alert["project"]):alerts.append(alert["project"]+": "+alert["detail"])
    answer="Evaluación técnica de solo lectura. "
    answer+=("Prioridad: revisar "+ "; ".join(alerts)+". " if alerts else "No se detectaron alertas en los datos consultados. Esto no certifica que los proyectos estén libres de errores. ")
    answer+=". ".join(rows) if rows else "No hay datos verificables para la selección."
    return {"text":answer[:3500],"project":projects[0] if len(projects)==1 else "","source":"GitHub y Railway","checked_at":data.get("checked_at")}
