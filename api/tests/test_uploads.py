from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import UploadFile

from app.routes import api as api_routes


@pytest.mark.asyncio
async def test_cloudinary_upload_returns_secure_url(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    def fake_config(**kwargs: object) -> None:
        calls["config"] = kwargs

    def fake_upload(*args: object, **kwargs: object) -> dict[str, str]:
        calls["upload"] = kwargs
        return {"secure_url": "https://res.cloudinary.com/example/image/upload/sample.jpg"}

    monkeypatch.setattr(
        api_routes,
        "get_settings",
        lambda: SimpleNamespace(
            max_upload_bytes=5_000_000,
            use_cloudinary=True,
            cloudinary_cloud_name="example",
            cloudinary_api_key="key",
            cloudinary_api_secret="secret",
            upload_dir=None,
        ),
    )
    monkeypatch.setattr(api_routes.cloudinary, "config", fake_config)
    monkeypatch.setattr(api_routes.cloudinary.uploader, "upload", fake_upload)

    upload = UploadFile(
        filename="sample.png",
        file=BytesIO(b"\x89PNG\r\n\x1a\nimage"),
        headers={"content-type": "image/png"},
    )
    result = await api_routes.save_post_image(upload)

    assert result.startswith("https://res.cloudinary.com/")
    assert calls["config"]
    assert calls["upload"] == {
        "folder": "safe-space-saturdays",
        "resource_type": "image",
        "format": "png",
    }
