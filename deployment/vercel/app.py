"""Stateless cloud inference; local Flask owns persistent request history."""
import hmac
import json
import logging
import os
import threading
from pathlib import Path

from flask import Flask, jsonify, request
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from inference import Predictor, validate_image, InvalidImage

ROOT=Path(__file__).resolve().parent
app=Flask(__name__)
# Leave headroom for multipart headers under Vercel's 4.5 MB request ceiling.
app.config['MAX_CONTENT_LENGTH']=4_000_000
_predictor=None
_lock=threading.Lock()

def predictor():
    global _predictor
    with _lock:
        if _predictor is None:
            manifest=json.loads((ROOT/'model/manifest.json').read_text())
            _predictor=Predictor(ROOT/'model/champion.keras',manifest['threshold'],
                                  manifest['registered_model']+':'+manifest['version'])
    return _predictor

@app.get('/health')
def health():
    manifest=json.loads((ROOT/'model/manifest.json').read_text())
    return jsonify(status='ok',project='l236050_A2_Ops',model_version=manifest['version'],
                   model_present=(ROOT/'model/champion.keras').is_file(),storage='stateless')

@app.post('/api/predict')
def predict():
    key=os.environ.get('API_KEY','')
    if not key or not hmac.compare_digest(request.headers.get('X-API-Key',''),key):
        return jsonify(error='An API key is required.'),401
    upload=request.files.get('image')
    if upload is None or not upload.filename:
        return jsonify(error='Select an image.'),400
    filename=secure_filename(upload.filename)[:255] or 'image'
    data=upload.read(app.config['MAX_CONTENT_LENGTH']+1)
    try:
        validate_image(data,filename)
    except InvalidImage as error:
        return jsonify(error=str(error)),400
    result=predictor().predict(data)
    logging.warning(json.dumps({'event':'prediction','filename':filename,**result}))
    return jsonify(**result,filename=filename)

@app.errorhandler(RequestEntityTooLarge)
def oversized(_error):
    return jsonify(error='The cloud API accepts requests below 4 MB.'),413
