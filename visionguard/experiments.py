"""Task 3: reproducible local/remote MLflow training and registry operations."""
import argparse
import gc
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("KERAS_HOME", str(ROOT / "artifacts/keras_cache"))
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("MLFLOW_ENABLE_ARTIFACTS_PROGRESS_BAR", "false")
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
for stream in [sys.stdout, sys.stderr]:
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

import matplotlib.pyplot as plt
import mlflow
import mlflow.tensorflow
import numpy as np
import pandas as pd
import tensorflow as tf
from dotenv import load_dotenv, set_key
from mlflow import MlflowClient
from PIL import Image, ImageOps
from sklearn.metrics import (
    ConfusionMatrixDisplay, accuracy_score, confusion_matrix, f1_score,
    precision_score, recall_score, roc_auc_score, roc_curve,
)
from sklearn.model_selection import train_test_split
from tensorflow import keras
from tensorflow.keras import layers

load_dotenv(ROOT / ".env")
SEED = 42
PROJECT = os.getenv("PROJECT_NAME", "l236050_A2_Ops")
OUTPUT = ROOT / "artifacts/task3"
OUTPUT.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "cashbowman/ai-generated-images-vs-real-images/versions/1"
SIZE = (128, 128)
keras.utils.set_random_seed(SEED)
tf.config.experimental.enable_op_determinism()
try:
    tf.config.threading.set_intra_op_parallelism_threads(8)
    tf.config.threading.set_inter_op_parallelism_threads(2)
except RuntimeError:
    pass


def git_sha():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def set_tracking(remote):
    if remote:
        uri = os.environ["MLFLOW_TRACKING_URI"]
    else:
        (ROOT / "mlflow_data").mkdir(exist_ok=True)
        uri = "sqlite:///" + (ROOT / "mlflow_data/mlflow.db").as_posix()
    mlflow.set_tracking_uri(uri)
    return uri


def experiment(name, remote=True):
    set_tracking(remote)
    client = MlflowClient()
    exp = client.get_experiment_by_name(name)
    if exp is None:
        location = None if remote else (ROOT / "mlflow_data/artifacts" / name).as_uri()
        experiment_id = client.create_experiment(name, artifact_location=location)
    else:
        experiment_id = exp.experiment_id
    mlflow.set_experiment(experiment_id=experiment_id)
    return experiment_id


class ManualMetrics(keras.callbacks.Callback):
    def on_epoch_end(self, epoch, logs=None):
        values = {key: float(value) for key, value in (logs or {}).items()}
        values["learning_rate"] = float(keras.backend.get_value(self.model.optimizer.learning_rate))
        mlflow.log_metrics(values, step=epoch)


def package_model(model, example, destination):
    """Use a standard MLflow model directory, also compatible with older servers."""
    prediction = model(example, training=False).numpy()
    signature = mlflow.models.infer_signature(example, prediction)
    mlflow.tensorflow.save_model(
        model, path=str(destination), signature=signature,
        pip_requirements=[f"{name}=={importlib.metadata.version(name)}"
                          for name in ["tensorflow", "keras", "numpy"]],
    )


def curve(history, path, title):
    best = int(np.argmin(history["val_loss"])) + 1
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.5))
    epochs = np.arange(1, len(history["loss"]) + 1)
    for ax, metric in zip(axes, ["loss", "accuracy"]):
        ax.plot(epochs, history[metric], label="Training")
        ax.plot(epochs, history["val_" + metric], label="Validation")
        ax.axvline(best, color="black", linestyle="--", label=f"Best epoch {best}")
        ax.set(xlabel="Epoch", ylabel=metric)
        ax.legend(fontsize=8)
        ax.grid(alpha=.2)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return best


def toy(remote):
    exp_id = experiment(PROJECT + ("_remote_toy" if remote else "_local_toy"), remote)
    (images, labels), _ = keras.datasets.fashion_mnist.load_data()
    indices, _ = train_test_split(np.arange(len(labels)), train_size=3750,
                                  random_state=SEED, stratify=labels)
    train, val = train_test_split(indices, test_size=750, random_state=SEED,
                                  stratify=labels[indices])
    x_train, x_val = images[train].astype("float32") / 255, images[val].astype("float32") / 255
    results = []
    for lr in ([1e-3] if remote else [1e-3, 1e-4]):
        keras.backend.clear_session()
        keras.utils.set_random_seed(SEED)
        name = f"toy_lr_{lr:g}"
        folder = OUTPUT / ("remote_toy" if remote else "local_toy") / name
        folder.mkdir(parents=True, exist_ok=True)
        with mlflow.start_run(run_name=name) as run:
            mlflow.log_params({"learning_rate": lr, "units": 64, "batch_size": 64,
                               "planned_epochs": 4, "training_examples": len(train)})
            mlflow.set_tags({"seed": str(SEED), "git_commit": git_sha(), "dataset": "Fashion-MNIST"})
            model = keras.Sequential([keras.Input((28, 28)), layers.Flatten(),
                                      layers.Dense(64, activation="relu"), layers.Dense(10, activation="softmax")])
            model.compile(optimizer=keras.optimizers.Adam(lr), loss="sparse_categorical_crossentropy", metrics=["accuracy"])
            history = model.fit(x_train, labels[train], validation_data=(x_val, labels[val]),
                                batch_size=64, epochs=4, callbacks=[ManualMetrics()], verbose=2)
            curve(history.history, folder / "curves.png", name)
            mlflow.log_artifact(str(folder / "curves.png"))
            with tempfile.TemporaryDirectory(dir=folder) as directory:
                packaged = Path(directory) / "model"
                package_model(model, x_train[:2], packaged)
                mlflow.log_artifacts(str(packaged), artifact_path="model")
            results.append({"name": name, "run_id": run.info.run_id,
                            "experiment_id": exp_id, "val_accuracy": history.history["val_accuracy"][-1]})
    path = OUTPUT / ("remote_toy.json" if remote else "local_toy.json")
    path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


_cache = {}


def decode(path, label):
    def read(value):
        with Image.open(value.decode()) as image:
            image.seek(0)
            return np.asarray(ImageOps.exif_transpose(image).convert("RGB"), dtype=np.uint8)
    image = tf.numpy_function(read, [path], tf.uint8)
    image.set_shape([None, None, 3])
    return tf.image.resize_with_pad(image, *SIZE, antialias=True), tf.cast(label, tf.float32)


def dataset(name, augment=False):
    frame = pd.read_csv(ROOT / f"splits/{name}.csv")
    if name not in _cache:
        ds = tf.data.Dataset.from_tensor_slices(([str(DATA / path) for path in frame.path], frame.label.to_numpy()))
        options = tf.data.Options()
        options.threading.private_threadpool_size = 4
        options.experimental_deterministic = True
        _cache[name] = ds.with_options(options).map(decode, num_parallel_calls=4).cache()
    ds = _cache[name]
    if name == "train":
        ds = ds.shuffle(len(frame), seed=SEED, reshuffle_each_iteration=True)
    ds = ds.batch(16)
    if augment:
        augmentation = keras.Sequential([
            layers.RandomFlip("horizontal", seed=SEED),
            layers.RandomRotation(.05, fill_mode="reflect", seed=SEED+1),
            layers.RandomZoom(.1, fill_mode="reflect", seed=SEED+2),
            layers.RandomContrast(.1, seed=SEED+3),
        ])
        ds = ds.map(lambda x, y: (tf.clip_by_value(augmentation(x, training=True), 0, 255), y), num_parallel_calls=4)
    return ds.prefetch(2)


def build(config):
    model = keras.models.load_model(ROOT / "artifacts/transfer_frozen.keras", compile=False)
    model.get_layer("head_dropout").rate = config["dropout"]
    base = next(layer for layer in model.layers if isinstance(layer, keras.Model))
    base.trainable = True
    for layer in base.layers:
        layer.trainable = False
    if config["unfrozen_layers"]:
        eligible = [layer for layer in base.layers if isinstance(layer, (layers.Conv2D, layers.DepthwiseConv2D))]
        for layer in eligible[-config["unfrozen_layers"]:]:
            layer.trainable = True
    model.compile(optimizer=keras.optimizers.Adam(config["learning_rate"]), loss="binary_crossentropy",
                  metrics=[keras.metrics.BinaryAccuracy(name="accuracy"), keras.metrics.AUC(name="auc")])
    return model


def threshold(labels, probabilities):
    candidates = np.unique(np.r_[0, .5, 1, probabilities, np.nextafter(probabilities, np.inf)])
    choices = []
    for value in candidates:
        predicted = probabilities >= value
        _, fp, fn, _ = confusion_matrix(labels, predicted, labels=[0, 1]).ravel()
        cost = (2 * fp + fn) / len(labels)
        choices.append((cost, -f1_score(labels, predicted, zero_division=0), abs(value-.5), float(value)))
    best = min(choices)
    return best[-1], best[0]


def project(epochs=6):
    experiment(PROJECT)
    base = {"learning_rate": 3e-4, "dropout": .4, "augmentation": True, "unfrozen_layers": 0}
    configurations = [
        ("reference_manual", {}, "manual"),
        ("lower_lr_autolog", {"learning_rate": 1e-4}, "autolog"),
        ("dropout_02_manual", {"dropout": .2}, "manual"),
        ("dropout_06_autolog", {"dropout": .6}, "autolog"),
        ("no_augmentation_manual", {"augmentation": False}, "manual"),
        ("unfreeze_4_autolog", {"unfrozen_layers": 4}, "autolog"),
    ]
    train_labels = pd.read_csv(ROOT / "splits/train.csv").label
    weights = {int(label): len(train_labels)/(2*count) for label, count in train_labels.value_counts().items()}
    data_version = next(line.split(":", 1)[1].strip() for line in (ROOT/"cashbowman.dvc").read_text().splitlines() if "md5:" in line)
    summaries = []
    for name, overrides, logging in configurations:
        folder = OUTPUT / name
        folder.mkdir(exist_ok=True)
        complete = folder / "result.json"
        if complete.exists():
            summaries.append(json.loads(complete.read_text()))
            print("Reusing completed run:", name, flush=True)
            continue
        config = {**base, **overrides}
        keras.backend.clear_session()
        keras.utils.set_random_seed(SEED)
        mlflow.tensorflow.autolog(disable=True)
        if logging == "autolog":
            mlflow.tensorflow.autolog(log_models=False, log_datasets=False, checkpoint=False, silent=True)
        with mlflow.start_run(run_name=name) as run:
            mlflow.log_params({**config, "image_size": 128, "batch_size": 16, "planned_epochs": epochs,
                               "warm_start": "Task2_best_frozen_checkpoint", "logging_method": logging})
            mlflow.set_tags({"git_commit": git_sha(), "dvc_data_version": data_version, "seed": str(SEED),
                             "project": PROJECT, "positive_class": "AI-generated", "comparison": "one_factor_from_reference"})
            model = build(config)
            callbacks = [keras.callbacks.EarlyStopping(monitor="val_loss", patience=3, restore_best_weights=True),
                         keras.callbacks.ModelCheckpoint(str(folder/"best.keras"), monitor="val_loss", save_best_only=True),
                         keras.callbacks.ReduceLROnPlateau(monitor="val_loss", patience=2, factor=.5, min_lr=1e-7)]
            if logging == "manual":
                callbacks.append(ManualMetrics())
            history = model.fit(dataset("train", config["augmentation"]), validation_data=dataset("validation"),
                                epochs=epochs, class_weight=weights, callbacks=callbacks, verbose=2)
            model = keras.models.load_model(folder / "best.keras")
            best_epoch = curve(history.history, folder / "curves.png", name)
            pd.DataFrame(history.history).to_csv(folder/"history.csv", index=False)
            val_labels = pd.read_csv(ROOT/"splits/validation.csv").label.to_numpy()
            val_prob = model.predict(dataset("validation"), verbose=0).ravel().astype(float)
            cutoff, val_cost = threshold(val_labels, val_prob)
            val_auc = roc_auc_score(val_labels, val_prob)
            mlflow.log_metrics({"validation_cost": val_cost, "validation_ROC_AUC": val_auc,
                                "decision_threshold": cutoff, "best_epoch": best_epoch})
            # Exactly one pass per newly trained model; Task 2 cached predictions are untouched.
            test_labels = pd.read_csv(ROOT/"splits/test.csv").label.to_numpy()
            test_prob = model.predict(dataset("test"), verbose=0).ravel().astype(float)
            np.savez(folder/"test_predictions.npz", labels=test_labels, probabilities=test_prob)
            predicted = test_prob >= cutoff
            metrics = {"test_accuracy": accuracy_score(test_labels, predicted),
                       "test_precision": precision_score(test_labels, predicted, zero_division=0),
                       "test_recall": recall_score(test_labels, predicted, zero_division=0),
                       "test_F1": f1_score(test_labels, predicted, zero_division=0),
                       "test_ROC_AUC": roc_auc_score(test_labels, test_prob)}
            mlflow.log_metrics(metrics)
            fig, ax = plt.subplots(figsize=(5, 4))
            ConfusionMatrixDisplay.from_predictions(test_labels, predicted, labels=[0, 1], display_labels=["Real", "AI"], colorbar=False, ax=ax)
            ax.set_title(name)
            fig.tight_layout();fig.savefig(folder/"confusion.png", dpi=140);plt.close(fig)
            fpr, tpr, _ = roc_curve(test_labels, test_prob)
            fig, ax = plt.subplots(figsize=(5, 4))
            ax.plot(fpr, tpr, label=f"AUC {metrics['test_ROC_AUC']:.3f}");ax.plot([0,1],[0,1],"--",color="gray")
            ax.set(xlabel="False positive rate",ylabel="True positive rate",title=name);ax.legend()
            fig.tight_layout();fig.savefig(folder/"roc.png",dpi=140);plt.close(fig)
            for filename in ["curves.png", "history.csv", "confusion.png", "roc.png"]:
                mlflow.log_artifact(str(folder/filename), artifact_path="evidence")
            mlflow.log_artifacts(str(ROOT/"splits"), artifact_path="splits")
            packages = subprocess.check_output([str(Path(os.sys.executable)), "-m", "pip", "freeze"], text=True)
            (folder/"packages.txt").write_text(packages, encoding="utf-8")
            mlflow.log_artifact(str(folder/"packages.txt"))
            with tempfile.TemporaryDirectory(dir=folder) as directory:
                example = next(iter(dataset("validation")))[0][:1].numpy()
                packaged = Path(directory)/"model"
                package_model(model, example, packaged)
                mlflow.log_artifacts(str(packaged), artifact_path="model")
            result = {"name": name, "run_id": run.info.run_id, **config, "logging_method": logging,
                      "validation_cost": val_cost, "validation_ROC_AUC": val_auc,
                      "threshold": cutoff, "best_epoch": best_epoch, **metrics}
            complete.write_text(json.dumps(result, indent=2), encoding="utf-8")
            summaries.append(result)
            print("COMPLETED",name,run.info.run_id,flush=True)
        mlflow.tensorflow.autolog(disable=True)
        del model
        gc.collect()
    results = pd.DataFrame(summaries)
    results.to_csv(OUTPUT/"comparison.csv", index=False)
    # Selection is based on validation only, never on the test-score columns.
    ranked = results.sort_values(["validation_cost", "validation_ROC_AUC"], ascending=[True, False])
    (OUTPUT/"selection.json").write_text(json.dumps(ranked.iloc[0].to_dict(), indent=2), encoding="utf-8")
    print(results.to_string(index=False))


def registry():
    set_tracking(True)
    results = pd.read_csv(OUTPUT/"comparison.csv").sort_values(["validation_cost", "validation_ROC_AUC"], ascending=[True, False])
    client = MlflowClient()
    try:
        client.create_registered_model(PROJECT)
    except mlflow.exceptions.MlflowException as error:
        if "already exists" not in str(error).lower():
            raise
    versions = []
    # The runner-up is version 1; the best validation candidate becomes champion.
    for _, row in results.iloc[:2].iloc[::-1].iterrows():
        version = client.create_model_version(PROJECT, f"runs:/{row.run_id}/model", run_id=row.run_id)
        client.set_model_version_tag(PROJECT, version.version, "validation_cost", str(row.validation_cost))
        client.set_model_version_tag(PROJECT, version.version, "seed", str(SEED))
        versions.append({"version": version.version, "run_id": row.run_id, "name": row['name']})
    champion = versions[-1]
    client.set_registered_model_alias(PROJECT, "champion", champion["version"])
    resolved = client.get_model_version_by_alias(PROJECT, "champion")
    assert str(resolved.version) == str(champion['version'])
    winner = results.iloc[0]
    (ROOT/"model").mkdir(exist_ok=True)
    shutil.copyfile(OUTPUT/winner['name']/"best.keras", ROOT/"model/champion.keras")
    manifest = {"registered_model": PROJECT, "alias": "champion", "version": str(resolved.version),
                "run_id": winner.run_id, "threshold": float(winner.threshold), "image_size": [128,128],
                "positive_class": "AI-generated", "preprocessing": "EXIF transpose, RGB, resize_with_pad; normalization inside model"}
    (ROOT/"model/manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (OUTPUT/"registry.json").write_text(json.dumps({"versions": versions, "champion": manifest}, indent=2), encoding="utf-8")
    set_key(str(ROOT/".env"), "MODEL_THRESHOLD", str(manifest['threshold']))
    set_key(str(ROOT/".env"), "MODEL_VERSION", f"{PROJECT}:{resolved.version}")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["local-toy", "remote-toy", "project", "registry"])
    parser.add_argument("--epochs", type=int, default=6)
    args = parser.parse_args()
    if args.mode.endswith("toy"):
        toy(args.mode == "remote-toy")
    elif args.mode == "project":
        project(args.epochs)
    else:
        registry()
