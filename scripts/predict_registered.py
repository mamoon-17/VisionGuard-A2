"""Load a model by the champion alias and classify one known image."""
import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
os.environ.setdefault('MLFLOW_ENABLE_ARTIFACTS_PROGRESS_BAR', 'false')
import mlflow
import mlflow.tensorflow

from visionguard.inference import CAVEAT, preprocess


def main():
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    args = parser.parse_args()
    name = os.getenv("PROJECT_NAME", "l236050_A2_Ops")
    uri = f"models:/{name}@champion"
    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    model = mlflow.tensorflow.load_model(uri)
    version = mlflow.MlflowClient().get_model_version_by_alias(name, "champion")
    threshold = float(version.tags['threshold'])
    probability = float(model(preprocess(args.image.read_bytes()), training=False).numpy().ravel()[0])
    print(json.dumps({"uri": uri, "version": version.version, "image": args.image.name,
                      "label": "AI-generated" if probability >= threshold else "Real",
                      "probability_ai": probability, "threshold": threshold, "caveat": CAVEAT}, indent=2))


if __name__ == "__main__":
    main()
