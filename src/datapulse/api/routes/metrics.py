"""GET /api/v1/_metrics — Prometheus text format (#734)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from datapulse.api.bootstrap.middleware import get_route_percentiles
from datapulse.rbac.dependencies import require_permission

router = APIRouter(tags=["observability"])


@router.get(
    "/_metrics",
    response_class=PlainTextResponse,
    dependencies=[Depends(require_permission("admin:metrics:read"))],
    summary="Prometheus latency metrics",
    description="Expose per-route p50/p95/p99 latency in Prometheus text format.",
)
def metrics() -> str:
    """Return per-route p50/p95/p99 latencies in Prometheus exposition format."""
    lines = [
        "# HELP datapulse_route_duration_ms Route latency histogram percentiles",
        "# TYPE datapulse_route_duration_ms gauge",
    ]
    for (method, path, status), pcts in get_route_percentiles().items():
        labels = f'method="{method}",path="{path}",status="{status}"'
        for pct_name, val in pcts.items():
            if pct_name == "count":
                # Expose sample count as a separate metric name for clarity
                lines.append(f"datapulse_route_requests_total{{{labels}}} {int(val)}")
            else:
                lines.append(
                    f'datapulse_route_duration_ms{{{labels},quantile="{pct_name}"}} {val:.2f}'
                )
    return "\n".join(lines) + "\n"
