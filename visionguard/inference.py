"""Load one local champion per process; use the training image transform."""
import io
import threading
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

ALLOWED = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP", "gif": "GIF"}
CAVEAT = "Experimental screening result. Images can be misclassified; this is not proof of authenticity."


class InvalidImage(ValueError):
    pass


def validate_image(data, filename):
    extension = Path(filename).suffix.lower().lstrip(".")
    if extension not in ALLOWED:
        raise InvalidImage("Choose a JPEG, PNG, WebP or GIF image.")
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format != ALLOWED[extension]:
                raise InvalidImage("The file contents do not match the image extension.")
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError, ValueError) as error:
        raise InvalidImage("The uploaded file could not be decoded as a valid image.") from error


def preprocess(data):
    import tensorflow as tf

    with Image.open(io.BytesIO(data)) as image:
        image.seek(0)
        pixels = np.asarray(ImageOps.exif_transpose(image).convert("RGB"), dtype=np.uint8)
    # Keep [0,255]; the exported model owns its MobileNet [-1,1] normalization.
    resized = tf.image.resize_with_pad(pixels, 128, 128, antialias=True)
    return tf.expand_dims(resized, 0)


class Predictor:
    def __init__(self, path, threshold, version):
        from tensorflow import keras

        self.model = keras.models.load_model(path, compile=False)
        self.threshold = float(threshold)
        self.version = version
        self.lock = threading.Lock()

    def predict(self, data):
        with self.lock:
            probability = float(self.model(preprocess(data), training=False).numpy().ravel()[0])
        is_ai = probability >= self.threshold
        return {"label": "AI-generated" if is_ai else "Real",
                "confidence": probability if is_ai else 1-probability,
                "probability_ai": probability, "threshold": self.threshold,
                "model_version": self.version, "caveat": CAVEAT}
