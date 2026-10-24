import json
import sys
from types import SimpleNamespace

import pytest

from src.core.infrastructure.providers.embeddings import SentenceTransformerEmbeddings


def test_missing_pooling_dimension_is_inferred_without_changing_model_files(tmp_path, monkeypatch):
    entries = [
        {"type": "sentence_transformers.models.Transformer", "path": ""},
        {"type": "sentence_transformers.models.Pooling", "path": "1_Pooling"},
        {"type": "sentence_transformers.models.Normalize", "path": "2_Normalize"},
    ]
    (tmp_path / "modules.json").write_text(json.dumps(entries))
    (tmp_path / "1_Pooling").mkdir()
    pooling_config = tmp_path / "1_Pooling/config.json"
    pooling_config.write_text('{"pooling_mode": "mean"}')
    (tmp_path / "sentence_bert_config.json").write_text('{"max_seq_length": 256, "do_lower_case": true}')

    class Transformer:
        def __init__(self, path, **kwargs):
            assert path == str(tmp_path)
            assert all(options["local_files_only"] for options in kwargs.values())
        def get_word_embedding_dimension(self):
            return 384

    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(models=SimpleNamespace(
        Transformer=Transformer, Pooling=lambda **kw: kw, Normalize=lambda: "normalize")))
    calls = []

    def load(*args, **kwargs):
        calls.append(kwargs)
        if args:
            raise TypeError("Pooling.__init__() missing 1 required positional argument: 'word_embedding_dimension'")
        return kwargs["modules"]

    modules = SentenceTransformerEmbeddings(tmp_path)._load_model(load)
    assert modules[0].max_seq_length == 256
    assert modules[0].do_lower_case is True
    assert modules[1] == {"pooling_mode": "mean", "word_embedding_dimension": 384}
    assert modules[2] == "normalize"
    assert pooling_config.read_text() == '{"pooling_mode": "mean"}'
    assert len(calls) == 2


def test_other_loading_errors_are_not_hidden(tmp_path):
    def load(*args, **kwargs):
        raise TypeError("unrelated model error")
    with pytest.raises(TypeError, match="unrelated model error"):
        SentenceTransformerEmbeddings(tmp_path)._load_model(load)


def test_regular_model_loading_keeps_offline_settings(tmp_path):
    def load(path, **kwargs):
        assert path == str(tmp_path)
        assert kwargs == {"device": "cpu", "trust_remote_code": False, "local_files_only": True}
        return "loaded"
    assert SentenceTransformerEmbeddings(tmp_path)._load_model(load) == "loaded"
