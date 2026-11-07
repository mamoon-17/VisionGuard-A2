"""Run on a GitHub-hosted runner to verify the API from another network."""
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import requests
from PIL import Image

if __name__=='__main__':
    base=os.environ.get('API_BASE_URL','https://l236050-a2-ops.vercel.app')
    health=requests.get(base+'/health',timeout=120)
    health.raise_for_status()
    image=io.BytesIO();Image.new('RGB',(64,64),(50,90,130)).save(image,format='PNG')
    result=requests.post(base+'/api/predict',files={'image':('network-smoke.png',image.getvalue(),'image/png')},
                         headers={'X-API-Key':os.environ['API_KEY']},timeout=180)
    result.raise_for_status()
    assert result.json()['label'] in ['Real','AI-generated']
    assert result.json()['model_version']=='l236050_A2_Ops:2'
    proof={'checked_at':datetime.now(timezone.utc).isoformat(),'network':'GitHub-hosted Ubuntu runner',
           'url':base+'/api/predict','health_status':health.status_code,'prediction_status':result.status_code,
           'response':result.json(),'purpose':'Network reachability, not a labelled accuracy evaluation'}
    Path('cloud-smoke.json').write_text(json.dumps(proof,indent=2))
    print(json.dumps(proof,indent=2))
