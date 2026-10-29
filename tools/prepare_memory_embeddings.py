"""Download the official MiniLM sentence model into the default local directory."""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from local_paths import EMBEDDING_MODEL


def main():
    repository = "sentence-transformers/all-MiniLM-L6-v2"
    with urllib.request.urlopen(f"https://huggingface.co/api/models/{repository}", timeout=60) as response:
        metadata = json.load(response)
    revision = metadata["sha"]
    required = {"config.json", "config_sentence_transformers.json", "modules.json",
                "sentence_bert_config.json", "special_tokens_map.json", "tokenizer.json",
                "tokenizer_config.json", "vocab.txt", "model.safetensors", "1_Pooling/config.json"}
    available = {entry["rfilename"] for entry in metadata["siblings"]}
    if required - available:
        raise RuntimeError(f"Missing model files: {required - available}")
    for name in sorted(required):
        destination = EMBEDDING_MODEL / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".download")
        print(f"Downloading {name}", flush=True)
        urllib.request.urlretrieve(f"https://huggingface.co/{repository}/resolve/{revision}/{name}", temporary)
        temporary.replace(destination)
    print(f"Ready: {EMBEDDING_MODEL} (revision {revision})", flush=True)


if __name__ == "__main__":
    main()
