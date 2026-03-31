"""
Graph metadata router.
GET /graph/stats  → vertex + edge counts from TigerGraph
GET /health       → ping TigerGraph, return status + latency_ms
"""
from typing import Any

from fastapi import APIRouter

from app.db.tigergraph import get_tg_connection, ping_tg
from app.core.logger import logger

router = APIRouter()


@router.get("/health")
def health() -> Any:
    """Ping TigerGraph and report connection status."""
    result = ping_tg()
    return result


@router.get("/stats")
def graph_stats() -> Any:
    """Return vertex and edge counts from TigerGraph."""
    conn = get_tg_connection()

    vertex_counts = {}
    edge_counts = {}

    vertex_types = ["User", "JobPost", "Skill", "Company"]
    for vt in vertex_types:
        try:
            stats = conn.getVertexStats(vt)
            count = 0
            if isinstance(stats, dict):
                for vals in stats.values():
                    if isinstance(vals, dict):
                        count += vals.get("count", 0)
                    elif isinstance(vals, int):
                        count = vals
            elif isinstance(stats, list) and stats:
                for item in stats:
                    count += item.get("count", 0)
            vertex_counts[vt] = count
        except Exception as e:
            logger.warning(f"Could not get stats for vertex type {vt}: {e}")
            vertex_counts[vt] = -1

    edge_types = ["HAS_SKILL", "REQUIRES_SKILL", "APPLIED_TO", "POSTED_BY", "SAVED"]
    for et in edge_types:
        try:
            ec = conn.getEdgeCount(et)
            if isinstance(ec, dict):
                edge_counts[et] = sum(ec.values())
            else:
                edge_counts[et] = ec or 0
        except Exception as e:
            logger.warning(f"Could not get count for edge type {et}: {e}")
            edge_counts[et] = -1

    total_vertices = sum(v for v in vertex_counts.values() if v >= 0)
    total_edges = sum(v for v in edge_counts.values() if v >= 0)

    return {
        "graph": "graphhire",
        "vertices": vertex_counts,
        "edges": edge_counts,
        "total_vertices": total_vertices,
        "total_edges": total_edges,
    }
