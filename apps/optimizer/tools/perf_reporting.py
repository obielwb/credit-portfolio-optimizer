

from __future__ import annotations

import gc
import json
import time
import traceback
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from evaluation import approved_limit_floor
from models import ModelParameters
from perf_config import validate_active_clustering
from pipeline import run_pipeline


def utc_now_iso() -> str:






    return datetime.now(timezone.utc).isoformat()


def dumps_json(data: Any) -> str:


    def _default(obj: Any) -> Any:


        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        raise TypeError(f"Object is not serializable: {type(obj)!r}")

    return json.dumps(data, indent=2, ensure_ascii=False, default=_default)


def approval_rate(result, parameters: ModelParameters) -> float:










    if not result.clients:
        return 0.0
    floor = approved_limit_floor(parameters)
    approved = sum(1 for r in result.clients if r.suggested_limit >= floor)
    return approved / len(result.clients)


def contagem_approval(result, parameters: ModelParameters) -> dict[str, int]:










    floor = approved_limit_floor(parameters)
    approved = sum(1 for r in result.clients if r.suggested_limit >= floor)
    denied = len(result.clients) - approved
    return {"approved": approved, "denied": denied}


def clustering_dict(parameters: ModelParameters, result) -> dict:










    return {
        "enabled": bool(parameters.enabled),
        "min_clusters": parameters.min_clusters,
        "max_clients_per_cluster": parameters.max_clients_per_cluster,
        "n_clusters": parameters.n_clusters,
        "total_clusters": len(result.clusters),
        "algorithm_cluster": "kmeans",
    }


def portfolio_dict(result, parameters: ModelParameters) -> dict:










    return {
        "total_clients": len(result.clients),
        "total_clusters": len(result.clusters),
        "total_limit": float(result.total_limit),
        "total_income": float(result.total_income),
        "total_loss": float(result.total_loss),
        "total_return": float(result.total_return),
        "financial_default_rate": float(result.financial_default_rate),
        "baseline_default_rate": float(
            result.baseline_default_rate
        ),
        "approval_rate": approval_rate(result, parameters),
        **contagem_approval(result, parameters),
        "approved_limit_floor": approved_limit_floor(parameters),
        "algorithm_result": result.algorithm,
    }


def format_duration(seconds: float) -> str:









    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{int(minutes)}m {secs:.1f}s"
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours)}h {int(minutes)}m {secs:.0f}s"


def write_markdown_report(path: Path, report: dict, *, title: str | None = None) -> None:








    meta = report["run_meta"]
    portfolio = report.get("portfolio") or {}
    heading = title or f"{meta.get('n_clients', 0):,} clients"
    lines = [
        f"# Performance report — {heading}",
        "",
        f"- **Status:** {meta['status']}",
        f"- **Algorithm:** {meta['algorithm']}",
    ]
    if meta.get("source"):
        lines.append(f"- **Source:** `{meta['source']}`")
    if meta.get("file"):
        lines.append(f"- **File:** `{meta['file']}`")
    lines.extend(
        [
            f"- **Started:** {meta['started_at']}",
            f"- **Finished:** {meta.get('finished_at', '—')}",
            f"- **Time total:** {format_duration(meta.get('elapsed_seconds') or 0)}",
        ]
    )
    if meta.get("ingestion_seconds") is not None:
        lines.append(
            f"- **Ingestion:** {format_duration(meta['ingestion_seconds'])}"
        )
    if meta.get("pipeline_seconds") is not None:
        lines.append(
            f"- **Pipeline:** {format_duration(meta['pipeline_seconds'])}"
        )
    if meta.get("file_rows") is not None:
        lines.append(f"- **File rows:** {meta['file_rows']:,}")
    if meta.get("clients_after_preprocessing") is not None:
        lines.append(
            f"- **Clients after preprocessing:** "
            f"{meta['clients_after_preprocessing']:,}"
        )
    if meta.get("clients_removed_by_filter"):
        lines.append(
            f"- **Removed (filter_flag=1):** "
            f"{meta['clients_removed_by_filter']:,}"
        )
    if meta.get("clients_after_ingestion") is not None:
        lines.append(
            f"- **Eligible pipeline clients:** {meta['clients_after_ingestion']:,}"
        )
    lines.append("")

    if meta.get("error"):
        lines.extend(["## Error", "", f"```\n{meta['error']}\n```", ""])
    cluster = report.get("clustering") or {}
    if cluster:
        lines.extend(
            [
                "## Clustering",
                "",
                f"- **Enabled:** {cluster.get('enabled')}",
                f"- **Generated clusters:** {cluster.get('total_clusters', 0):,}",
                f"- **min_clusters (config):** {cluster.get('min_clusters')}",
                f"- **max_clients_per_cluster:** {cluster.get('max_clients_per_cluster')}",
                "",
            ]
        )
    if portfolio:
        lines.extend(
            [
                "## Portfolio results",
                "",
                "| Metric | Value |",
                "|---|---|",
                f"| Clients | {portfolio.get('total_clients', 0):,} |",
                f"| Clusters | {portfolio.get('total_clusters', 0):,} |",
                f"| Limit total | R$ {portfolio.get('total_limit', 0):,.2f} |",
                f"| Income total | R$ {portfolio.get('total_income', 0):,.2f} |",
                f"| Loss total | R$ {portfolio.get('total_loss', 0):,.2f} |",
                f"| Return total | R$ {portfolio.get('total_return', 0):,.2f} |",
                f"| Financial default rate | {portfolio.get('financial_default_rate', 0):.4f} |",
                f"| Approved (>= {portfolio.get('approved_limit_floor', 200):.0f}) | {portfolio.get('approved', 0):,} |",
                f"| Negados (limit 0) | {portfolio.get('denied', 0):,} |",
                f"| Approval rate | {100 * portfolio.get('approval_rate', 0):.2f}% |",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_summary_md(path: Path, summary: dict, *, title: str = "performance benchmark") -> None:








    lines = [
        f"# Summary — {title}",
        "",
        f"- **Session:** {summary['session_id']}",
        f"- **Algorithm:** {summary['algorithm']}",
    ]
    if summary.get("bases"):
        lines.append(f"- **Bases:** {', '.join(f'`{b}`' for b in summary['bases'])}")
    elif summary.get("source"):
        lines.append(f"- **Source:** `{summary['source']}`")
    lines.extend(
        [
            f"- **Started:** {summary['started_at']}",
            f"- **Finished:** {summary.get('finished_at', '—')}",
            f"- **Time total:** {format_duration(summary.get('total_elapsed_seconds', 0))}",
            "",
            "## Runs",
            "",
            "| Dataset | Clients | Status | Ingestion | Pipeline | Total | Clusters | Approval |",
            "|---|---:|---|---:|---:|---:|---:|---:|",
        ]
    )
    for run in summary["runs"]:
        c = run.get("portfolio") or {}
        cl = run.get("clustering") or {}
        meta = run["run_meta"]
        base = meta.get("source") or "—"
        total_str = (
            format_duration(meta["elapsed_seconds"])
            if meta.get("elapsed_seconds") is not None
            else "—"
        )
        ingest_str = (
            format_duration(meta["ingestion_seconds"])
            if meta.get("ingestion_seconds") is not None
            else "—"
        )
        pipe_str = (
            format_duration(meta["pipeline_seconds"])
            if meta.get("pipeline_seconds") is not None
            else "—"
        )
        rate = c.get("approval_rate")
        rate_str = f"{100 * rate:.1f}%" if rate is not None else "—"
        lines.append(
            f"| `{base}` "
            f"| {meta.get('n_clients', 0):,} "
            f"| {meta['status']} "
            f"| {ingest_str} "
            f"| {pipe_str} "
            f"| {total_str} "
            f"| {cl.get('total_clusters', c.get('total_clusters', 0)):,} "
            f"| {rate_str} |"
        )
    lines.extend(["", "## Portfolio results by dataset", ""])
    if summary["runs"]:
        lines.extend(
            [
                "| Base | Limit total | Return total | Inad. fin. | Approved | Negados | Rate approval. |",
                "|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for run in summary["runs"]:
            c = run.get("portfolio") or {}
            meta = run["run_meta"]
            base = meta.get("source") or "—"
            rate = c.get("approval_rate")
            rate_str = f"{100 * rate:.2f}%" if rate is not None else "—"
            lines.append(
                f"| `{base}` "
                f"| R$ {c.get('total_limit', 0):,.2f} "
                f"| R$ {c.get('total_return', 0):,.2f} "
                f"| {c.get('financial_default_rate', 0):.4f} "
                f"| {c.get('approved', 0):,} "
                f"| {c.get('denied', 0):,} "
                f"| {rate_str} |"
            )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def run_pipeline_benchmark(
    *,
    algorithm: str,
    parameters: ModelParameters,
    clients,
    run_meta: dict[str, Any],
    validate_clustering: bool = True,
) -> dict:


    started_at = utc_now_iso()
    t0 = time.monotonic()
    report: dict = {
        "run_meta": {
            **run_meta,
            "algorithm": algorithm,
            "started_at": started_at,
            "finished_at": None,
            "elapsed_seconds": None,
            "status": "running",
            "error": None,
        },
        "parameters": asdict(parameters),
        "portfolio": None,
    }

    try:
        t_pipeline = time.monotonic()
        result = run_pipeline(
            None,
            algorithm,
            parameters,
            clients=clients,
        )
        if validate_clustering:
            validate_active_clustering(result, parameters, len(clients))
        pipeline_elapsed = time.monotonic() - t_pipeline
        elapsed = time.monotonic() - t0

        report["clustering"] = clustering_dict(parameters, result)
        report["portfolio"] = portfolio_dict(result, parameters)
        report["run_meta"]["pipeline_seconds"] = round(pipeline_elapsed, 3)
        report["run_meta"]["elapsed_seconds"] = round(elapsed, 3)
        report["run_meta"]["finished_at"] = utc_now_iso()
        report["run_meta"]["status"] = "success"
    except MemoryError as exc:
        elapsed = time.monotonic() - t0
        report["run_meta"]["elapsed_seconds"] = round(elapsed, 3)
        report["run_meta"]["finished_at"] = utc_now_iso()
        report["run_meta"]["status"] = "oom"
        report["run_meta"]["error"] = (
            f"{type(exc).__name__}: {exc} — reduce the portfolio size or disable clustering (enabled=False)"
        )
    except Exception as exc:
        elapsed = time.monotonic() - t0
        report["run_meta"]["elapsed_seconds"] = round(elapsed, 3)
        report["run_meta"]["finished_at"] = utc_now_iso()
        report["run_meta"]["status"] = "error"
        report["run_meta"]["error"] = f"{type(exc).__name__}: {exc}"
        report["run_meta"]["traceback"] = traceback.format_exc()
    finally:
        gc.collect()

    return report


def persist_report(
    out_dir: Path,
    report: dict,
    stem: str,
    *,
    title: str | None = None,
) -> list[Path]:
    """Write run JSON and Markdown and return the output paths."""

    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / f"{stem}.json"
    md_path = out_dir / f"{stem}.md"

    json_path.write_text(dumps_json(report), encoding="utf-8")
    write_markdown_report(md_path, report, title=title)

    return [json_path, md_path]
