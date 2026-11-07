"""Provision immutable serving assets before deploying; never contact registry per request."""
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    target=ROOT/'deployment/vercel'
    (target/'model').mkdir(exist_ok=True)
    for name in ['champion.keras','manifest.json']:
        shutil.copyfile(ROOT/'model'/name,target/'model'/name)
    shutil.copyfile(ROOT/'visionguard/inference.py',target/'inference.py')
    print('Vercel inference code and champion assets prepared.')
