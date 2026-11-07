"""Deploy the provisioned API without putting secret values on command lines."""
import sys
import subprocess
from pathlib import Path
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'deployment/vercel'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')

def command(args,value=None):
    result=subprocess.run(['vercel.cmd',*args],cwd=TARGET,input=value,text=True,encoding='utf-8',errors='replace',
                          stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    print(result.stdout,flush=True)
    result.check_returncode()
    return result.stdout

if __name__=='__main__':
    values=dotenv_values(ROOT/'.env')
    current=command(['env','ls','production'])
    if 'API_KEY' not in current:
        command(['env','add','API_KEY','production','--sensitive'],values['API_KEY']+'\n')
    if 'VERCEL_SUPPORT_LARGE_FUNCTIONS' not in current:
        command(['env','add','VERCEL_SUPPORT_LARGE_FUNCTIONS','production'],'1\n')
    output=command(['deploy','--prod','--yes','--build-env','VERCEL_SUPPORT_LARGE_FUNCTIONS=1'])
    (ROOT/'evidence/vercel-deploy.log').write_text(output,encoding='utf-8')
