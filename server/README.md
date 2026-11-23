# JARVIS Brain API (experimental)

Endpoints: GET /health (public); GET /projects and GET/POST /lessons (Bearer JARVIS_API_TOKEN required).

**Security:** never commit tokens. Set JARVIS_API_TOKEN in Railway variables. Without token, protected endpoints are disabled. The database defaults to /tmp and **is ephemeral**; configure a persistent volume and JARVIS_DB_PATH before real training. This is a training API prototype, not an autonomous AI model, and projects are catalog-only, not connected.
