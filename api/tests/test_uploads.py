from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import UploadFile
from PIL import Image

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
            max_source_upload_bytes=40_000_000,
            use_cloudinary=True,
            cloudinary_cloud_name="example",
            cloudinary_api_key="key",
            cloudinary_api_secret="secret",
            upload_dir=None,
        ),
    )
    monkeypatch.setattr(api_routes.cloudinary, "config", fake_config)
    monkeypatch.setattr(api_routes.cloudinary.uploader, "upload", fake_upload)

    source = BytesIO()
    Image.new("RGB", (80, 80), (224, 180, 140)).save(source, format="PNG")
    source.seek(0)
    upload = UploadFile(
        filename="sample.png",
        file=source,
        headers={"content-type": "image/png"},
    )
    result = await api_routes.save_post_image(upload)

    assert result.startswith("https://res.cloudinary.com/")
    assert calls["config"]
    assert calls["upload"] == {
        "folder": "safe-space-saturdays",
        "resource_type": "image",
        "format": "webp",
    }


def test_normalise_upload_keeps_output_within_limit() -> None:
    source = BytesIO()
    Image.new("RGB", (1800, 1200), (120, 160, 140)).save(source, format="PNG")

    output = api_routes.normalise_upload(source.getvalue(), max_bytes=20_000)

    assert len(output) <= 20_000
    with Image.open(BytesIO(output)) as image:
        assert image.format == "WEBP"
        assert image.width <= 2400
        assert image.height <= 2400
