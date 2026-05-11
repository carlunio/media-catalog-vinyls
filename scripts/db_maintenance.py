from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


def _file_size_mb(path: Path) -> float:
    if not path.exists():
        return 0.0
    return path.stat().st_size / (1024 * 1024)


def main() -> int:
    parser = argparse.ArgumentParser(description="DuckDB maintenance for media-catalog-vinyls")
    parser.add_argument(
        "--db",
        default="data/vinyls.duckdb",
        help="Path to DuckDB file (default: data/vinyls.duckdb)",
    )
    parser.add_argument(
        "--repack",
        action="store_true",
        help="Create a compact rebuilt copy as <db>.repacked.duckdb",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace original DB with repacked copy (requires --repack)",
    )
    args = parser.parse_args()
    if args.replace and not args.repack:
        raise SystemExit("--replace requires --repack")

    db_path = Path(args.db).expanduser().resolve()
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")

    before_mb = _file_size_mb(db_path)
    print(f"DB: {db_path}")
    print(f"Size before: {before_mb:.2f} MB")

    with duckdb.connect(str(db_path)) as con:
        # Persist old versions to stable storage and then reclaim free space.
        con.execute("CHECKPOINT")
        con.execute("VACUUM")

        try:
            info = con.execute("PRAGMA database_size").fetchall()
            if info:
                print(f"PRAGMA database_size: {info[0]}")
        except Exception:
            pass

    after_mb = _file_size_mb(db_path)
    delta_mb = after_mb - before_mb
    print(f"Size after: {after_mb:.2f} MB")
    print(f"Delta: {delta_mb:+.2f} MB")

    repacked_path: Path | None = None
    if args.repack:
        repacked_path = db_path.with_suffix(".repacked.duckdb")
        if repacked_path.exists():
            repacked_path.unlink()

        with duckdb.connect(str(db_path)) as con:
            db_list = con.execute("PRAGMA database_list").fetchall()
            if not db_list:
                raise SystemExit("Unable to resolve current DuckDB catalog name for repack")
            catalog_name = str(db_list[0][1])
            con.execute(f"ATTACH '{repacked_path.as_posix()}' AS repacked")
            con.execute(f'COPY FROM DATABASE "{catalog_name}" TO repacked')
            con.execute("DETACH repacked")

        repacked_mb = _file_size_mb(repacked_path)
        print(f"Repacked copy: {repacked_path}")
        print(f"Repacked size: {repacked_mb:.2f} MB")

    if args.replace and repacked_path is not None:
        if not repacked_path.exists():
            raise SystemExit(f"Repacked file not found: {repacked_path}")
        backup_path = db_path.with_suffix(".pre_repack.bak.duckdb")
        if backup_path.exists():
            backup_path.unlink()
        db_path.replace(backup_path)
        repacked_path.replace(db_path)
        final_mb = _file_size_mb(db_path)
        print(f"Original DB moved to backup: {backup_path}")
        print(f"Replacement complete. New DB size: {final_mb:.2f} MB")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
