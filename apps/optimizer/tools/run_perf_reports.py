#!/usr/bin/env python3















from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from perf_config import generate_benchmark_clients, parameters_benchmark  # noqa: E402
from tools.perf_reporting import (  # noqa: E402
    dumps_json,
    format_duration,
    persist_report,
    run_pipeline_benchmark,
    utc_now_iso,
    write_summary_md,
)

DEFAULT_SIZES = (100, 1000, 10000, 100_000, 1_000_000)


def _run_single(n: int, algorithm: str, parameters) -> dict:











    t0 = time.monotonic()
    clients = generate_benchmark_clients(n)
    gen_elapsed = time.monotonic() - t0

    report = run_pipeline_benchmark(
        algorithm=algorithm,
        parameters=parameters,
        clients=clients,
        run_meta={
            "n_clients": n,
            "ingestion_seconds": round(gen_elapsed, 3),
            "clients_gerados_em_s": round(gen_elapsed, 3),
        },
    )
    if report["run_meta"]["status"] == "success":
        report["run_meta"]["elapsed_seconds"] = round(
            gen_elapsed + report["run_meta"]["pipeline_seconds"], 3
        )
    return report


def main() -> int:







    parser = argparse.ArgumentParser(description="Pipeline benchmark with reports.")
    parser.add_argument(
        "--sizes",
        default=os.getenv("PERF_SIZES", ",".join(str(s) for s in DEFAULT_SIZES)),
        help="Comma-separated sizes (default: 100,1000,10000,100000,1000000)",
    )
    parser.add_argument(
        "--algorithm",
        default=os.getenv("PERF_ALGORITHM", "simplex"),
        choices=("simplex", "simplex_ortools", "branch_bound"),
    )
    parser.add_argument(
        "--output-dir",
        default=os.getenv("PERF_OUTPUT_DIR", "reports/performance"),
        help="Base directory (creates a timestamped subdirectory)",
    )
    args = parser.parse_args()

    sizes = [int(s.strip()) for s in args.sizes.split(",") if s.strip()]
    session_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_dir = Path(args.output_dir).resolve() / session_id
    out_dir.mkdir(parents=True, exist_ok=True)

    parameters = parameters_benchmark()
    algorithm = args.algorithm

    print(f"Performance session: {session_id}")
    print(f"Output: {out_dir.resolve()}")
    print(f"Sizes: {sizes}")
    print(f"Algorithm: {algorithm}\n")

    summary: dict = {
        "session_id": session_id,
        "algorithm": algorithm,
        "parameters": asdict(parameters),
        "started_at": utc_now_iso(),
        "finished_at": None,
        "total_elapsed_seconds": None,
        "sizes": sizes,
        "runs": [],
    }

    session_t0 = time.monotonic()
    for n in sizes:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] n={n:,} — iniciando...")
        sys.stdout.flush()

        report = _run_single(n, algorithm, parameters)
        summary["runs"].append(report)

        (out_dir / "summary.partial.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        persist_report(out_dir, report, stem=f"n_{n}")

        meta = report["run_meta"]
        if meta["status"] == "success":
            c = report["portfolio"]
            print(
                f"  OK em {format_duration(meta['elapsed_seconds'])} "
                f"| limit={c['total_limit']:,.0f} "
                f"| return={c['total_return']:,.0f} "
                f"| approval={100 * c['approval_rate']:.0f}%"
            )
        elif meta["status"] == "oom":
            print(f"  OOM (memory): {meta.get('error')}")
        else:
            print(f"  ERROR: {meta.get('error')}")
        print()
        sys.stdout.flush()

    summary["finished_at"] = utc_now_iso()
    summary["total_elapsed_seconds"] = round(time.monotonic() - session_t0, 3)

    (out_dir / "summary.json").write_text(dumps_json(summary), encoding="utf-8")
    write_summary_md(out_dir / "REPORT.md", summary)

    print(f"Completed. Reports em:\n  {out_dir.resolve()}")
    return 0 if all(r["run_meta"]["status"] == "success" for r in summary["runs"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
