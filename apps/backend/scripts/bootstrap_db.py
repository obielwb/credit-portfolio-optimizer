#!/usr/bin/env python3


from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap the database through ORM models (SQLAlchemy create_all and seed)."
    )
    parser.add_argument(
        "--no-seed",
        action="store_true",
        help="Create tables without inserting default parameters.",
    )
    args = parser.parse_args()

    try:
        from src.utils.db.bootstrap import bootstrap_database
    except Exception as exc:
        print(f"Error importing bootstrap: {exc}", file=sys.stderr)
        return 1

    try:
        _, seeded_id = bootstrap_database(seed=not args.no_seed, configure_session=True)
    except Exception as exc:
        print(f"Bootstrap failed: {exc}", file=sys.stderr)
        return 1

    print("Schema created from ORM models.")
    if args.no_seed:
        print("Seed ignorado (--no-seed).")
    elif seeded_id is None:
        print("Seed: parameters already existed; no record was created.")
    else:
        print(f"Seed: parameters default created (id={seeded_id}).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
