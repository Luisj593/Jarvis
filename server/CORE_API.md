# JARVIS Core HTTP (development only)

Deployment build context: repository root, Dockerfile at /Dockerfile.
The service now copies `core/` and `server/` together. Legacy
`/health`, `/chat`, `/lessons`, `/projects` remain available.

All `/v1/core/*` endpoints use the existing Bearer token authentication
from server/app.py. Configure `JARVIS_API_TOKEN` and `JARVIS_OWNER_ID`
in Railway; if owner is missing, core routes return 503. Owner and
permissions are **server-defined**, never taken from request JSON.

GET: `/v1/core/projects`, `/v1/core/actions`, `/v1/core/audit`.
POST: `/v1/core/projects` (name,objective);
`/v1/core/conversation/select` (session_id,project);
`/v1/core/conversation/respond` (session_id,message);
`/v1/core/actions/policy` (project_id,allowed,expected_version);
`/v1/core/actions/preview` (project_id,action,params);
`/v1/core/actions/confirm` (ticket,confirmation).

The core uses strict per-project policies. Grant explicit permission before
previewing actions. High-risk actions require reinforced confirmation.
Responses do not run actions.

**Security limitations:** one server-side owner and one shared Bearer token;
no individual user accounts, rotation, request rate limits or Android auth.
The core remains a deterministic proof of integration, not a production
multi-user API. Audit GET may expose sensitive project metadata to anyone
with the token. Use only a private development environment and do not expose
tokens in logs. The old /chat and /lessons use a separate legacy lessons
table and are NOT migrated to the core learning model.

Run: `PYTHONPATH=core python -m unittest discover -s core/tests -v`.
