"""R2 solo acepta URLs firmadas con SigV4."""
import types

from app.core import storage


def test_url_firmada_usa_sigv4(monkeypatch):
    monkeypatch.setattr(
        storage,
        "get_settings",
        lambda: types.SimpleNamespace(
            r2_endpoint="https://abc.r2.cloudflarestorage.com",
            r2_access_key_id="AKIAFAKE",
            r2_secret_access_key="secretfake",
            r2_bucket="elogistics",
        ),
    )
    storage._client.cache_clear()
    try:
        url = storage.url_firmada("acuses/x/prueba.pdf")
    finally:
        storage._client.cache_clear()
    assert "X-Amz-Algorithm=AWS4-HMAC-SHA256" in url
    assert "AWSAccessKeyId=" not in url
