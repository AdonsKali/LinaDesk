"""Real model smoke check; uses only the configured local model."""
import asyncio
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.core.infrastructure.providers.embeddings import SentenceTransformerEmbeddings
from src.core.infrastructure.repositories.sqlite_memory_repository import SQLiteMemoryRepository
from src.core.domain.value_objects.memory_fragment import MemoryFragment, MemoryZone, MemorySource


async def main():
    root = Path(__file__).resolve().parents[1]
    settings = json.loads((root / "data/settings.json").read_text(encoding="utf-8-sig"))
    embeddings = SentenceTransformerEmbeddings(settings.get("embedding_model_path"))
    try:
        await check(embeddings)
    finally:
        await embeddings.close()


async def check(embeddings):
    vector = await embeddings.embed_query("Лина вспоминает разговор")
    assert len(vector) == 384
    assert abs(sum(x*x for x in vector) - 1) < 1e-4
    with tempfile.TemporaryDirectory() as directory:
        repo = SQLiteMemoryRepository(Path(directory) / "memory.sqlite3", embeddings)
        for content in ["A spider frightened Lina.", "The user enjoys pizza.", "The weather is sunny today."]:
            await repo.upsert_fragment(MemoryFragment.create(zone=MemoryZone.USER_FACTS,
                content=content, importance=.8, source=MemorySource.CONVERSATION))
        found = await repo.search(MemoryZone.USER_FACTS, "Lina was scared of an eight-legged creature", 1)
        assert found[0].content == "A spider frightened Lina."
        print(json.dumps({"model": embeddings.model_id, "dimensions": len(vector),
                          "semantic_match": found[0].content, "status": "passed"}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
