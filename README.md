# l236050_A2_Ops

[![VisionGuard CI](https://github.com/mamoon-17/VisionGuard-A2/actions/workflows/ci.yml/badge.svg)](https://github.com/mamoon-17/VisionGuard-A2/actions/workflows/ci.yml)

VisionGuard classifies an uploaded image as real or AI-generated. The result is experimental and is not proof of authenticity.

Code and CI: https://github.com/mamoon-17/VisionGuard-A2  
DagsHub code, data, MLflow and registry: https://dagshub.com/mamoon-17/VisionGuard-A2

## Run

Use Python 3.12. Create a virtual environment, install `requirements-web.txt` (Windows: omit Gunicorn and install Waitress), copy `.env.example` to `.env`, and replace the example passwords and keys. `.env` is ignored by Git and Docker.

Provision the champion once with `dvc pull model/champion.keras.dvc`, after configuring your DagsHub DVC credentials with `dvc remote modify --local`. The model is mounted read-only and loaded once per worker; inference never contacts the registry.

Run `docker compose up --build -d` and open http://127.0.0.1:5000. PostgreSQL is private to the Compose network and stores history in the named `history_data` volume. `docker compose down` preserves that volume. Avoid `down -v` when you want to retain history.

For a local SQLite UI run `waitress-serve --listen=127.0.0.1:5002 app:app` on Windows. Set `REMOTE_INFERENCE_URL` to the deployed `/api/predict` URL to use cloud inference; keep the API key in `.env`. Uploads stay in memory.

## Training and verification

Tasks 1–2: `l236050.ipynb`; Task 3: `python -m visionguard.experiments local-toy`, `remote-toy`, `project`, then `registry`. Remote tracking uses the three `MLFLOW_TRACKING_*` environment variables. A registry export selects by validation cost, never by test scores.

Alias prediction: `python -m scripts.predict_registered <image>`; local smoke check: `python -m scripts.predict_local`.

Checks: `python -m pip install -r requirements-test.txt`, `ruff check visionguard scripts tests app.py`, `python -m pytest -q`. CI also builds the CPU-only Docker image. The GitHub repository's Actions secret `DAGSHUB_TOKEN` mirrors successful main-branch builds to DagsHub; secrets are injected at runtime and never stored in the workflow.

`submission a2` is an ignored local hand-in folder. Raw images, model binaries, credentials, databases and evidence captures are excluded from Git; DVC pointers track the dataset and champion.
