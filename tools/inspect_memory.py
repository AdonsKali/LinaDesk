"""Read-only inventory of the local semantic memory, without exposing its text."""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from local_paths import BASE_DIR


def main():
    path = BASE_DIR / "data/memory.sqlite3"
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
        result = {"path": str(path), "bytes": path.stat().st_size,
                  "memories_by_zone": dict(db.execute("SELECT zone, COUNT(*) FROM memories GROUP BY zone")),
                  "vectors_by_model": dict(db.execute("SELECT model, COUNT(*) FROM vectors GROUP BY model")),
                  "vector_dimensions": [row[0] for row in db.execute(
                      "SELECT DISTINCT json_array_length(vector) FROM vectors")],
                  "orphan_vectors": db.execute("SELECT COUNT(*) FROM vectors WHERE id NOT IN (SELECT id FROM memories)").fetchone()[0]}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
