"""Call the public deployment with real validation images; keep credentials private."""
import json
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import requests
from dotenv import dotenv_values, set_key

ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    values=dotenv_values(ROOT/'.env')
    base='https://l236050-a2-ops.vercel.app'
    health=requests.get(base+'/health',timeout=120)
    print('Cloud health:',health.status_code,health.text[:400],flush=True)
    health.raise_for_status()
    frame=pd.read_csv(ROOT/'splits/validation.csv')
    data=ROOT/'cashbowman/ai-generated-images-vs-real-images/versions/1'
    folder=ROOT/'evidence/cloud-samples';folder.mkdir(exist_ok=True)
    results=[]
    for label in [0,1]:
        row=next(row for _,row in frame[frame.label==label].iterrows() if (data/row.path).stat().st_size<3_500_000)
        source=data/row.path
        target=folder/('real' if label==0 else 'ai')
        target=target.with_suffix(source.suffix)
        target.write_bytes(source.read_bytes())
        with source.open('rb') as stream:
            response=requests.post(base+'/api/predict',headers={'X-API-Key':values['API_KEY']},
                files={'image':(source.name,stream)},timeout=180)
        print('Cloud prediction:',response.status_code,response.text[:650],flush=True)
        response.raise_for_status()
        results.append({'folder_label':int(label),'filename':source.name,'fixture':str(target.relative_to(ROOT)),
                        'http_status':response.status_code,'response':response.json()})
    (ROOT/'evidence/cloud-verification.json').write_text(json.dumps({'checked_at':datetime.now(timezone.utc).isoformat(),
        'base_url':base,'health':health.json(),'predictions':results},indent=2),encoding='utf-8')
    set_key(str(ROOT/'.env'),'REMOTE_INFERENCE_URL',base+'/api/predict')
    set_key(str(ROOT/'.env'),'DATABASE_URL','sqlite:///instance/cloud_history.db')
    print('Cloud verified; local Flask is configured to call the public API.')
