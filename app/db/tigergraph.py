"""
TigerGraph REST API client for GraphHire.
Uses requests directly with JWT bearer token — avoids pyTigerGraph 2.x init bugs.
"""
import time
import logging
import requests
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Lazy token cache ─────────────────────────────────────────────────────────
_token: Optional[str] = None


def _get_token() -> str:
    """Return a valid JWT token, refreshing via secret if needed."""
    global _token
    if _token:
        return _token

    # Try to get a fresh token using the secret
    if settings.TG_SECRET:
        try:
            url = f"{settings.TG_HOST}/gsql/v1/tokens"
            resp = requests.post(
                url,
                json={"secret": settings.TG_SECRET},
                timeout=10,
                verify=True,
            )
            if resp.ok:
                data = resp.json()
                _token = data.get("token") or data.get("results", {}).get("token")
                if _token:
                    logger.info("TigerGraph token obtained via secret.")
                    return _token
        except Exception as e:
            logger.warning(f"Token refresh via secret failed: {e}")

    # Fall back to the JWT from .env
    if settings.TG_JWT_TOKEN:
        _token = settings.TG_JWT_TOKEN
        logger.info("Using TG_JWT_TOKEN from .env.")
        return _token

    raise RuntimeError("No TigerGraph token available — set TG_SECRET or TG_JWT_TOKEN in .env")


def _headers() -> dict:
    return {"Authorization": f"Bearer {_get_token()}", "Content-Type": "application/json"}


def _base() -> str:
    return settings.TG_HOST.rstrip("/")


def _graph_base() -> str:
    return f"{_base()}/restpp"


# ── Core REST helpers ─────────────────────────────────────────────────────────

def tg_get(path: str, params: dict = None) -> Any:
    url = f"{_graph_base()}{path}"
    resp = requests.get(url, headers=_headers(), params=params or {}, timeout=15, verify=True)
    resp.raise_for_status()
    return resp.json()


def tg_post(path: str, body: Any) -> Any:
    url = f"{_graph_base()}{path}"
    resp = requests.post(url, headers=_headers(), json=body, timeout=15, verify=True)
    resp.raise_for_status()
    data = resp.json()
    # Log any logical errors (common in TigerGraph REST)
    if "results" in data:
        results = data["results"]
        if isinstance(results, list) and results:
            item = results[0]
            accepted = item.get("accepted_vertices", item.get("accepted_edges", -1))
            if accepted == 0:
                logger.warning(f"TigerGraph UPSERT returned 0 accepted instances: {data}")
    return data


def tg_put(path: str, body: Any) -> Any:
    """PUT request — required for single-vertex/edge upsert endpoints."""
    url = f"{_graph_base()}{path}"
    resp = requests.put(url, headers=_headers(), json=body, timeout=15, verify=True)
    resp.raise_for_status()
    data = resp.json()
    logger.debug(f"TG PUT {path} → {data}")
    return data


# ── Graph operations ──────────────────────────────────────────────────────────

GRAPH = property(lambda self: settings.TG_GRAPH)
_G = lambda: settings.TG_GRAPH  # noqa: E731


def _wrap_attrs(attributes: dict) -> dict:
    """Wrap attribute values in {"value": v} format required by TigerGraph bulk upsert."""
    return {k: {"value": v} for k, v in (attributes or {}).items()}


def upsert_vertex(vertex_type: str, vertex_id: str, attributes: dict) -> dict:
    """Upsert a vertex via the bulk POST /graph/{g} endpoint with correct attribute format."""
    body = {
        "vertices": {
            vertex_type: {
                vertex_id: _wrap_attrs(attributes)
            }
        }
    }
    result = tg_post(f"/graph/{_G()}", body)
    logger.info(f"upsert_vertex({vertex_type}, {vertex_id}) → {result}")
    return result


def upsert_edge(
    from_type: str, from_id: str,
    edge_type: str,
    to_type: str, to_id: str,
    attributes: dict = None,
) -> dict:
    """Upsert an edge via the bulk POST /graph/{g} endpoint with correct attribute format."""
    body = {
        "edges": {
            from_type: {
                from_id: {
                    edge_type: {
                        to_type: {
                            to_id: _wrap_attrs(attributes or {})
                        }
                    }
                }
            }
        }
    }
    result = tg_post(f"/graph/{_G()}", body)
    logger.info(f"upsert_edge({from_type}/{from_id} -[{edge_type}]-> {to_type}/{to_id}) → {result}")
    return result


def get_vertices(
    vertex_type: str,
    where: str = None,
    select: str = None,
    limit: int = 100,
) -> list:
    params = {"limit": limit}
    if where:
        params["filter"] = where
    if select:
        params["select"] = select
    resp = tg_get(f"/graph/{_G()}/vertices/{vertex_type}", params=params)
    return resp.get("results", [])


def get_vertex_by_id(vertex_type: str, vertex_id: str) -> Optional[dict]:
    try:
        resp = tg_get(f"/graph/{_G()}/vertices/{vertex_type}/{vertex_id}")
        results = resp.get("results", [])
        return results[0] if results else None
    except Exception:
        return None


def get_edges(from_type: str, from_id: str, edge_type: str) -> list:
    resp = tg_get(f"/graph/{_G()}/edges/{from_type}/{from_id}/{edge_type}")
    return resp.get("results", [])


def get_neighbors(
    source_type: str,
    source_id: str,
    edge_type: str = None,
    target_vertex_type: str = None,
    limit: int = 100
) -> list:
    """Fetch neighbor vertices with full attributes using installed queries where possible."""
    # Special optimization for User's interacted jobs (Saved/Applied/Reported)
    if source_type == "User" and target_vertex_type == "JobPost":
        try:
            res = run_installed_query("get_user_jobs", params={
                "p_userId": str(source_id),
                "p_edgeType": str(edge_type)
            })
            # get_user_jobs returns [{"Results": [...]}]
            for item in res:
                if "Results" in item:
                    return item["Results"]
            return []
        except Exception as e:
            logger.error(f"Error calling get_user_jobs: {e}")
            return []

    # Fallback: Basic edge traversal (does NOT return full attributes by default)
    path = f"/graph/{_G()}/vertices/{source_type}/{source_id}/neighbors"
    params = {"limit": limit}
    if edge_type:
        params["edgeType"] = edge_type
    if target_vertex_type:
        params["targetVertexType"] = target_vertex_type
    
    try:
        resp = tg_get(path, params=params)
        return resp.get("results", [])
    except Exception as e:
        logger.error(f"get_neighbors fallback failed: {e}")
        return []


def get_vertex_count(vertex_type: str = None) -> dict:
    if vertex_type:
        resp = tg_get(f"/graph/{_G()}/vertices/{vertex_type}", params={"limit": 0, "count_only": True})
        return {vertex_type: resp.get("count", 0)}
    # Get counts for all known types
    types = ["User", "JobPost", "Skill", "Company"]
    counts = {}
    for vt in types:
        try:
            resp = tg_get(f"/graph/{_G()}/vertices/{vt}", params={"limit": 0, "count_only": True})
            counts[vt] = resp.get("count", 0)
        except Exception:
            counts[vt] = -1
    return counts


def get_edge_count() -> dict:
    edge_types = ["HAS_SKILL", "REQUIRES_SKILL", "APPLIED_TO", "POSTED_BY", "SAVED"]
    counts = {}
    try:
        resp = tg_get(f"/graph/{_G()}/edges")
        for item in resp.get("results", []):
            et = item.get("e_type", "")
            if et in edge_types:
                counts[et] = counts.get(et, 0) + 1
    except Exception as e:
        logger.warning(f"Edge count failed: {e}")
        for et in edge_types:
            counts[et] = -1
    return counts


def run_installed_query(query_name: str, params: dict = None) -> list:
    resp = tg_get(f"/query/{_G()}/{query_name}", params=params or {})
    return resp.get("results", [])


# ── Health check ──────────────────────────────────────────────────────────────

def ping_tg() -> dict:
    start = time.monotonic()
    try:
        resp = requests.get(
            f"{_base()}/restpp/graph/{_G()}/vertices/Company",
            headers=_headers(),
            params={"limit": 1},
            timeout=8,
            verify=True,
        )
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        if resp.ok:
            return {"status": "connected", "latency_ms": latency_ms}
        return {"status": "error", "detail": resp.text[:200], "latency_ms": latency_ms}
    except Exception as e:
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        logger.error(f"TigerGraph ping failed: {e}")
        return {"status": "error", "detail": str(e), "latency_ms": latency_ms}


# ── Compatibility shim for old get_tg_connection() call sites ─────────────────
class _TGShim:
    """Minimal shim so existing code using get_tg_connection() still works."""
    def upsertVertex(self, vtype, vid, attributes=None):
        return upsert_vertex(vtype, vid, attributes or {})

    def upsertEdge(self, from_type, from_id, edge_type, to_type, to_id, attributes=None):
        return upsert_edge(from_type, from_id, edge_type, to_type, to_id, attributes or {})

    def getVertices(self, vtype, where=None, select=None, limit=100):
        return get_vertices(vtype, where=where, select=select, limit=limit)

    def getVerticesById(self, vtype, ids: list):
        results = []
        for vid in ids:
            v = get_vertex_by_id(vtype, str(vid))
            if v:
                results.append(v)
        return results

    def getEdges(self, from_type, from_id, edge_type):
        return get_edges(from_type, from_id, edge_type)

    def runInstalledQuery(self, query_name, params=None):
        return run_installed_query(query_name, params)

    def getNeighbors(self, source_type, source_id, edgeType=None, targetVertexType=None, limit=100):
        return get_neighbors(source_type, source_id, edgeType, targetVertexType, limit)

    def getVertexStats(self, vtype):
        counts = get_vertex_count(vtype)
        return counts

    def getEdgeCount(self, edge_type=None):
        counts = get_edge_count()
        if edge_type:
            return {edge_type: counts.get(edge_type, 0)}
        return counts


_shim = _TGShim()


def get_tg_connection() -> _TGShim:
    """Return a connection shim — validates token on first call."""
    _get_token()  # ensures token is resolved early
    return _shim


def get_next_skill_id() -> int:
    """
    Returns the next sequential integer ID for a skill.
    We fetch all existing skills and find the max ID.
    Starts from 1 if no skills exist.
    """
    conn = get_tg_connection()
    # Fetch all skills from the Skill vertex type
    skills = conn.getVertices("Skill", limit=10000)
    if not skills:
        return 1
    
    ids = []
    for s in skills:
        try:
            ids.append(int(s["v_id"]))
        except (ValueError, TypeError):
            continue
            
    if not ids:
        return 1
        
    return max(ids) + 1


def get_all_skills_list():
    """
    Fetches all skills as a list of {id, name} objects for the frontend dropdown.
    Deduplicates by name to ensure each skill name appears only once.
    """
    conn = get_tg_connection()
    skills = conn.getVertices("Skill", limit=5000)
    
    unique_skills = {}
    for s in skills:
        name = s.get("attributes", {}).get("name", "Unknown").strip()
        skill_id = int(s["v_id"])
        # If we have duplicates, keep the one with the lower ID or just the first seen
        if name not in unique_skills:
            unique_skills[name] = skill_id
            
    return [{"id": sid, "name": name} for name, sid in sorted(unique_skills.items())]


def ensure_skill_exists(name: str, category: str = "user_defined", allow_create: bool = False) -> Optional[int]:
    """
    Checks if a skill with the given name exists (case-insensitive).
    Returns the existing ID if found.
    If not found and allow_create=True, creates a new one and returns it.
    Otherwise returns None.
    """
    conn = get_tg_connection()
    # Case-insensitive name search
    res = conn.getVertices("Skill", where=f"name == \"{name}\"")
    if res:
        return int(res[0]["v_id"])
    
    if not allow_create:
        return None

    # Create new sequential ID
    new_id = get_next_skill_id()
    conn.upsertVertex("Skill", new_id, attributes={
        "skillId": new_id,
        "name": str(name),
        "category": str(category)
    })
    return new_id


def get_skill_by_id(skill_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a skill by its ID. Returns {id, name} or None."""
    conn = get_tg_connection()
    res = conn.getVerticesById("Skill", [str(skill_id)])
    if res:
        return {
            "id": int(res[0]["v_id"]),
            "name": res[0]["attributes"].get("name", "Unknown")
        }
    return None


def generate_skill_id(name: str) -> Optional[int]:
    """
    Backward compatibility wrapper. Now just calls ensure_skill_exists with allow_create=False.
    """
    return ensure_skill_exists(name, allow_create=False)

