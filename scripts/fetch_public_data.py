from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.services.public_data import PublicDataClient


DATASETS = {
    "checkup": "checkup_dataset_path",
    "group-checkup": "checkup_group_dataset_path",
}


async def fetch_pages(dataset: str, pages: int, per_page: int) -> list[dict]:
    settings = get_settings()
    client = PublicDataClient(settings)
    path = getattr(settings, DATASETS[dataset])
    rows: list[dict] = []
    for page in range(1, pages + 1):
        payload = await client.fetch_json(path, page=page, per_page=per_page)
        rows.extend(payload.get("data", []))
        print(f"page={page} rows={len(payload.get('data', []))} total_collected={len(rows)}")
    return rows


def write_csv(rows: list[dict], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=DATASETS.keys(), default="checkup")
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--per-page", type=int, default=100)
    parser.add_argument("--out", default="data/checkup_sample.csv")
    args = parser.parse_args()

    rows = asyncio.run(fetch_pages(args.dataset, args.pages, args.per_page))
    write_csv(rows, Path(args.out))
    print(f"saved {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
