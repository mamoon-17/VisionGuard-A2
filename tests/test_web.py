import io

import pytest
from PIL import Image

from visionguard.web import create_app


class FakePredictor:
    def predict(self, _data):
        return {"label": "AI-generated", "confidence": .8, "probability_ai": .8,
                "threshold": .65, "model_version": "test:2"}


def png():
    stream = io.BytesIO()
    Image.new("RGB", (32, 16), "red").save(stream, format="PNG")
    return stream.getvalue()


@pytest.fixture
def app():
    return create_app({"TESTING": True, "DATABASE_URL": "sqlite:///:memory:",
                       "API_KEY": "test-key", "REMOTE_INFERENCE_URL": "",
                       "MAX_CONTENT_LENGTH": 1024*1024}, predictor=FakePredictor())


def test_success_is_logged_and_filename_sanitized(app):
    client = app.test_client()
    response = client.post("/api/predict", headers={"X-API-Key": "test-key"},
        data={"image": (io.BytesIO(png()), "../../unsafe.png")})
    assert response.status_code == 200
    assert response.json["filename"] == "unsafe.png"
    rows = app.extensions["db"].recent()
    assert len(rows) == 1 and rows[0]["model_version"] == "test:2"
    assert rows[0]["confidence"] == .8 and rows[0]["content_sha256"]


@pytest.mark.parametrize("filename,data", [("wrong.txt", b"text"), ("broken.png", b"not an image"), ("wrong.jpg", png())])
def test_invalid_uploads_are_rejected_and_logged(app, filename, data):
    response = app.test_client().post("/predict", data={"image": (io.BytesIO(data), filename)})
    assert response.status_code == 400
    assert app.extensions["db"].recent()[0]["status"] == "rejected"


def test_oversized_request_has_friendly_error(app):
    response = app.test_client().post("/predict", data={"image": (io.BytesIO(b"x"*(2*1024*1024)), "big.png")})
    assert response.status_code == 413
    assert b"size" in response.data.lower() or b"limit" in response.data.lower()


def test_api_requires_key(app):
    response = app.test_client().post("/api/predict", data={"image": (io.BytesIO(png()), "sample.png")})
    assert response.status_code == 401


def test_history_and_health(app):
    client = app.test_client()
    client.post("/predict", data={"image": (io.BytesIO(png()), "sample.png")})
    assert b"sample.png" in client.get("/history").data
    assert client.get("/health").json["status"] == "ok"


def test_database_persists_after_app_restart(tmp_path):
    database = "sqlite:///" + (tmp_path/"history.sqlite").as_posix()
    config = {"TESTING": True, "DATABASE_URL": database, "REMOTE_INFERENCE_URL": "", "API_KEY": ""}
    first = create_app(config, predictor=FakePredictor())
    first.test_client().post("/predict", data={"image": (io.BytesIO(png()), "persistent.png")})
    first.extensions["db"].engine.dispose()
    second = create_app(config, predictor=FakePredictor())
    assert b"persistent.png" in second.test_client().get("/history").data


def test_remote_ui_records_api_model_version(app, monkeypatch):
    class Response:
        def raise_for_status(self): pass
        def json(self): return FakePredictor().predict(b"")
    app.config["REMOTE_INFERENCE_URL"] = "https://example.invalid/api/predict"
    monkeypatch.setattr("visionguard.web.requests.post", lambda *args, **kwargs: Response())
    response = app.test_client().post("/predict", data={"image": (io.BytesIO(png()), "remote.png")})
    assert response.status_code == 200
    assert app.extensions["db"].recent()[0]["model_version"] == "test:2"
