from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.scrapers import load_sources, scan_all

WEB_DIR = ROOT / "web"
PUBLIC_DIR = ROOT
ASSETS_DIR = PUBLIC_DIR / "assets"
DATA_DIR = PUBLIC_DIR / "data"


def main() -> None:
    items, errors, source_count = scan_all()
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    shutil.copy2(WEB_DIR / "index.html", PUBLIC_DIR / "index.html")
    shutil.copy2(WEB_DIR / "app.js", ASSETS_DIR / "app.js")
    shutil.copy2(WEB_DIR / "styles.css", ASSETS_DIR / "styles.css")

    static_items = []
    for index, item in enumerate(sorted(items, key=lambda entry: entry.get("score", 0), reverse=True), start=1):
        static_items.append({**item, "id": index, "status": "nouveau"})

    payload = {
        "generated_at": generated_at,
        "items": static_items,
        "source_directory": load_sources().get("platform_directory", {}),
        "scans": [
            {
                "id": 1,
                "started_at": generated_at,
                "finished_at": generated_at,
                "source_count": source_count,
                "found_count": len(static_items),
                "saved_count": len(static_items),
                "errors": errors,
            }
        ],
    }
    (DATA_DIR / "opportunities.json").write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"Static site built with {len(static_items)} opportunities")


if __name__ == "__main__":
    main()
