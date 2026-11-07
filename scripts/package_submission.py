"""Assemble only the requested local hand-in materials; never stage this folder."""
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'submission a2'
TARGET.mkdir(exist_ok=True)

def local_values():
    result={}
    for line in (ROOT/'.env').read_text(encoding='utf-8').splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key,value=line.split('=',1);result[key]=value.strip().strip("\"'")
    return result

if __name__=='__main__':
    source_commit=json.loads((ROOT/'results/submission-source.json').read_text())['commit']
    current=ROOT/'Report.docx'
    backup=ROOT/'evidence/Report-before-concise.docx'
    if not backup.exists():shutil.copyfile(current,backup)
    shutil.copyfile(ROOT/'evidence/Report-concise.docx',current)
    shutil.copyfile(current,TARGET/'Report.docx')
    shutil.copyfile(ROOT/'evidence/Report-concise.pdf',TARGET/'l236050_VisionGuard.pdf')
    files=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    files=[name for name in files if name and name not in ['Report.docx','Assignment 2.pdf']]
    extra=['model/champion.keras','artifacts/task3/comparison.csv','artifacts/test_metrics.csv',
           'artifacts/toy_tuner_results.csv','artifacts/visionguard_tuner_results.csv',
           'artifacts/best_epochs.json','artifacts/evaluation_choices.json','artifacts/error_examples.csv']
    with zipfile.ZipFile(TARGET/'VisionGuard-source.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(set(files+extra)):
            path=ROOT/name
            if path.is_file():archive.write(path,arcname='VisionGuard-A2/'+name)
    (TARGET/'SUBMISSION.txt').write_text(
        'VISIONGUARD ASSIGNMENT 2\nRoll: l236050\n\n'
        'Required report: l236050_VisionGuard.pdf\nEditable copy: Report.docx\n'
        'Runnable code, executed notebook and champion: VisionGuard-source.zip\n\n'
        'GitHub: https://github.com/mamoon-17/VisionGuard-A2\n'
        'DagsHub: https://dagshub.com/mamoon-17/VisionGuard-A2\n'
        'Live API: https://l236050-a2-ops.vercel.app/api/predict\n'
        'Public health: https://l236050-a2-ops.vercel.app/health\n'
        'Graded source commit: '+source_commit+'\n'
        'External-network proof: https://github.com/mamoon-17/VisionGuard-A2/actions/runs/42407281894\n\n'
        'The API takes multipart field image and header X-API-Key. API_ACCESS.txt contains the private grading key. '
        'Keep that file out of public repositories. The source ZIP contains no credentials.\n\n'
        'Extract the ZIP, copy .env.example to .env, replace the placeholder passwords/keys, '
        'and run docker compose up --build -d. The champion is included, so this app start needs no DVC credentials. '
        'Open http://127.0.0.1:5000. For cloud integration set REMOTE_INFERENCE_URL in .env to the live API '
        'and API_KEY to the supplied access key, then run Waitress locally as described in README.\n\n'
        'Checks passed: nine app tests, Ruff, project CI/Docker build, six Postman assertions and an external-network prediction. '
        'The 33-page report includes only assignment evidence with concise explanations.\n\n'
        'This entire submission a2 folder is ignored by Git and remains local.\n',encoding='utf-8')
    values=local_values()
    (TARGET/'API_ACCESS.txt').write_text(
        'PRIVATE GRADING ACCESS\n\nAPI URL: https://l236050-a2-ops.vercel.app/api/predict\n'
        'Method: POST\nBody: multipart/form-data; field image is the uploaded file\n'
        'Header X-API-Key: '+values['API_KEY']+'\n\n'
        'This file is local only and is excluded from Git. Share it only with your assessor through the private submission channel.\n',encoding='utf-8')
    # Confirm the source archive contains none of the actual local credentials.
    secrets=[value.encode() for key,value in values.items()
             if key in ['API_KEY','SECRET_KEY','POSTGRES_PASSWORD','MLFLOW_TRACKING_PASSWORD'] and len(value)>15]
    with zipfile.ZipFile(TARGET/'VisionGuard-source.zip') as archive:
        for name in archive.namelist():
            content=archive.read(name)
            if any(secret in content for secret in secrets):raise RuntimeError('Credential found in source archive: '+name)
    print('Packaged submission; source archive credential scan passed.')
    for path in sorted(TARGET.iterdir()):print(path.name,path.stat().st_size,'bytes')
