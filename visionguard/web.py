"""Browser UI, inference API, validation and database-backed history."""
import hashlib
import hmac
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from .database import Database
from .inference import CAVEAT, InvalidImage, Predictor, validate_image

ROOT = Path(__file__).resolve().parents[1]


def create_app(config=None, predictor=None):
    load_dotenv(ROOT / ".env")
    app = Flask(__name__, template_folder=str(ROOT / "templates"), static_folder=str(ROOT / "static"))
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", "local-development-only"),
        MAX_CONTENT_LENGTH=int(os.getenv("MAX_CONTENT_LENGTH", "5242880")),
        DATABASE_URL=os.getenv("DATABASE_URL", "sqlite:///instance/history.db"),
        MODEL_PATH=os.getenv("MODEL_PATH", "model/champion.keras"),
        MODEL_THRESHOLD=float(os.getenv("MODEL_THRESHOLD", ".5")),
        MODEL_VERSION=os.getenv("MODEL_VERSION", "unknown"),
        REMOTE_INFERENCE_URL=os.getenv("REMOTE_INFERENCE_URL", ""),
        API_KEY=os.getenv("API_KEY", ""),
    )
    app.config.update(config or {})
    (ROOT / "instance").mkdir(exist_ok=True)
    app.extensions["db"] = Database(app.config["DATABASE_URL"])
    if predictor is not None:
        app.extensions["predictor"] = predictor
    elif not app.config["REMOTE_INFERENCE_URL"]:
        app.extensions["predictor"] = Predictor(app.config["MODEL_PATH"], app.config["MODEL_THRESHOLD"], app.config["MODEL_VERSION"])

    def reject(message, status, filename="rejected-upload"):
        app.extensions["db"].record(filename, "rejected", detail=message,
                                      result={"model_version": app.config["MODEL_VERSION"]})
        if request.path.startswith("/api/"):
            return jsonify(error=message), status
        return render_template("error.html", message=message, status=status), status

    @app.get("/")
    def upload():
        return render_template("upload.html")

    @app.post("/predict")
    @app.post("/api/predict")
    def predict():
        if request.path.startswith("/api/") and app.config["API_KEY"]:
            if not hmac.compare_digest(request.headers.get("X-API-Key", ""), app.config["API_KEY"]):
                return jsonify(error="An API key is required."), 401
        uploaded = request.files.get("image")
        if uploaded is None or not uploaded.filename:
            return reject("Select an image to upload.", 400)
        filename = secure_filename(uploaded.filename)[:255] or "image"
        data = uploaded.read(app.config["MAX_CONTENT_LENGTH"]+1)
        if len(data) > app.config["MAX_CONTENT_LENGTH"]:
            return reject("The image exceeds the size limit.", 413, filename)
        try:
            validate_image(data, filename)
        except InvalidImage as error:
            return reject(str(error), 400, filename)
        started = time.perf_counter()
        try:
            if app.config["REMOTE_INFERENCE_URL"] and not request.path.startswith("/api/"):
                response = requests.post(app.config["REMOTE_INFERENCE_URL"],
                    files={"image": (filename, data, uploaded.mimetype)},
                    headers={"X-API-Key": app.config["API_KEY"]}, timeout=(10, 90))
                response.raise_for_status()
                result = response.json()
                required = {"label", "confidence", "probability_ai", "model_version"}
                if not required.issubset(result):
                    raise ValueError("The inference API returned an incomplete result.")
            else:
                service = app.extensions.get("predictor")
                if service is None:
                    return reject("The local inference service is unavailable.", 503, filename)
                result = service.predict(data)
        except (requests.RequestException, ValueError) as error:
            app.logger.warning("Inference request failed: %s", type(error).__name__)
            return reject("The inference service could not complete this request. Try again shortly.", 502, filename)
        latency = (time.perf_counter()-started)*1000
        result.setdefault("caveat", CAVEAT)
        app.extensions["db"].record(filename, "success", digest=hashlib.sha256(data).hexdigest(),
                                      result=result, latency_ms=latency)
        if request.path.startswith("/api/"):
            return jsonify(**result, filename=filename, latency_ms=round(latency, 2))
        return render_template("result.html", result=result, filename=filename)

    @app.get("/history")
    def history():
        return render_template("history.html", rows=app.extensions["db"].recent())

    @app.get("/health")
    def health():
        app.extensions["db"].healthy()
        return jsonify(status="ok", model_version=app.config["MODEL_VERSION"],
                       inference="remote" if app.config["REMOTE_INFERENCE_URL"] else "local")

    @app.errorhandler(RequestEntityTooLarge)
    def oversized(_error):
        return reject("The image exceeds the 5 MiB request limit.", 413)

    @app.errorhandler(404)
    def missing(_error):
        return render_template("error.html", message="This page was not found.", status=404), 404

    return app
