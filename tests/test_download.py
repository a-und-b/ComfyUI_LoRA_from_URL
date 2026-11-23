import os

import pytest
import requests

import load_lora_url_node as mod

URL = "https://example.com/lora.safetensors"


class FakeResponse:
    def __init__(self, chunks, fail_after=None):
        self.headers = {"content-length": "0"}
        self._chunks, self._fail_after = chunks, fail_after

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        for i, c in enumerate(self._chunks):
            if i == self._fail_after:
                raise requests.ConnectionError("connection dropped")
            yield c

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def test_broken_download_is_not_cached(monkeypatch):
    node = mod.LoadLoraFromURL()
    responses = iter([FakeResponse([b"half", b"rest"], fail_after=1),
                      FakeResponse([b"half", b"rest"])])
    monkeypatch.setattr(mod.requests, "get", lambda *a, **k: next(responses))

    with pytest.raises(requests.ConnectionError):
        node.download_if_needed(URL)
    assert os.listdir(node.cache_dir) == []  # no partial file, no .part left

    path = node.download_if_needed(URL)
    with open(path, "rb") as f:
        assert f.read() == b"halfrest"


def test_request_has_timeout(monkeypatch):
    seen = {}

    def fake_get(*a, **k):
        seen.update(k)
        return FakeResponse([b"x"])

    monkeypatch.setattr(mod.requests, "get", fake_get)
    mod.LoadLoraFromURL().download_if_needed(URL)
    assert seen.get("timeout")


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://x/y", "", "example.com/a"])
def test_rejects_non_http_urls(url, monkeypatch):
    monkeypatch.setattr(mod.requests, "get", lambda *a, **k: pytest.fail("no request"))
    with pytest.raises(ValueError):
        mod.LoadLoraFromURL().download_if_needed(url)


def test_load_lora_raises_instead_of_passing_model_through(monkeypatch):
    monkeypatch.setattr(mod.requests, "get",
                        lambda *a, **k: (_ for _ in ()).throw(requests.ConnectionError("down")))
    with pytest.raises(requests.ConnectionError):
        mod.LoadLoraFromURL().load_lora(URL, object(), 1.0)
