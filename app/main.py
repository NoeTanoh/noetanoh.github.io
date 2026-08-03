from __future__ import annotations

import argparse
import csv
import io
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .scrapers import load_sources, scan_all
from .storage import (
    finish_scan,
    list_opportunities,
    recent_scans,
    start_scan,
    update_status,
    upsert_opportunities,
)


ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"

app = FastAPI(title="Gombo Opportunities", version="0.1.0")
app.mount("/assets", StaticFiles(directory=WEB_DIR), name="assets")


class StatusPayload(BaseModel):
    status: str


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (WEB_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/opportunities")
def opportunities(
    status: str = Query("all"),
    track: str = Query("all"),
    domain: str = Query("all"),
    min_score: int = Query(35, ge=0, le=100),
    q: str | None = Query(None),
) -> dict:
    return {
        "items": list_opportunities(status=status, track=track, domain=domain, min_score=min_score, query=q),
        "scans": recent_scans(5),
        "source_directory": load_sources().get("platform_directory", {}),
    }


@app.post("/api/scan")
def scan() -> dict:
    items, errors, source_count = scan_all()
    scan_id = start_scan(source_count)
    saved_count = upsert_opportunities(items)
    finish_scan(scan_id, len(items), saved_count, errors)
    return {
        "scan_id": scan_id,
        "found": len(items),
        "saved": saved_count,
        "errors": errors,
        "items": list_opportunities(min_score=35),
    }


@app.patch("/api/opportunities/{item_id}/status")
def set_status(item_id: int, payload: StatusPayload) -> dict:
    try:
        item = update_status(item_id, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not item:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return item


@app.get("/api/export.csv")
def export_csv() -> StreamingResponse:
    rows = list_opportunities(status="all", min_score=0, limit=10000)
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "status",
            "score",
            "title",
            "organization",
            "source",
            "location",
            "remote_type",
            "opportunity_type",
            "deadline",
            "posted_at",
            "url",
            "summary",
            "keywords",
        ],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({key: ",".join(row[key]) if key == "keywords" else row.get(key, "") for key in writer.fieldnames})
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=gombo-opportunities.csv"},
    )


def cli_scan() -> None:
    items, errors, source_count = scan_all()
    scan_id = start_scan(source_count)
    saved_count = upsert_opportunities(items)
    finish_scan(scan_id, len(items), saved_count, errors)
    print(f"Scan {scan_id}: {len(items)} remote opportunities found, {saved_count} saved")
    if errors:
        print("Errors:")
        for error in errors:
            print(f"- {error}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Gombo Opportunities utility")
    parser.add_argument("--scan", action="store_true", help="Run one scraping scan and save results")
    args = parser.parse_args()
    if args.scan:
        cli_scan()


if __name__ == "__main__":
    main()
