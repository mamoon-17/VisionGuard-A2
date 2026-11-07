"""Classify two known files with a single loaded local champion."""
import json
from pathlib import Path
import pandas as pd
from visionguard.inference import Predictor

def main():
    manifest=json.loads(Path('model/manifest.json').read_text())
    predictor=Predictor('model/champion.keras',manifest['threshold'],manifest['registered_model']+':'+manifest['version'])
    data=Path('cashbowman/ai-generated-images-vs-real-images/versions/1')
    frame=pd.read_csv('splits/validation.csv')
    for label in [0,1]:
        row=frame[frame.label==label].iloc[0]
        result=predictor.predict((data/row.path).read_bytes())
        print(json.dumps({'known_folder_label':'AI-generated' if label else 'Real','filename':Path(row.path).name,
                          'prediction':result['label'],'confidence':round(result['confidence'],4),
                          'probability_ai':round(result['probability_ai'],4),'model':result['model_version']}))

if __name__=='__main__': main()
