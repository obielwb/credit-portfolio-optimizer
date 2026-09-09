

from __future__ import annotations

import asyncio

from src.workers.optimization_worker import run_optimization_worker
from src.utils.db.bootstrap import bootstrap_database


async def main() -> None:
    """Start the optimization worker loop."""
    bootstrap_database(ensure_schema=False, seed=False)
    bootstrap_database(seed=False)
    await run_optimization_worker(continuous=True)


if __name__ == "__main__":
    asyncio.run(main())
