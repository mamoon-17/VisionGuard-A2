"""Run real commands in a native console and capture the resulting window."""
import argparse
from pathlib import Path
from scripts.capture_console import capture

ROOT = Path(__file__).resolve().parents[1]

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('name')
    parser.add_argument('commands', help='UTF-8 PowerShell command file')
    args = parser.parse_args()
    title = f'l236050_A2_Ops evidence {args.name}'
    content = Path(args.commands).read_text(encoding='utf-8')
    script = ROOT/'evidence/terminal_scripts'/f'{args.name}.ps1'
    script.parent.mkdir(parents=True,exist_ok=True)
    preamble = f'''$ErrorActionPreference = 'Stop'
$Host.UI.RawUI.WindowTitle = '{title}'
Set-Location -LiteralPath '{ROOT}'
$env:TF_CPP_MIN_LOG_LEVEL = '3'
$env:PYTHONIOENCODING = 'utf-8'
Write-Host ('l236050_A2_Ops | mamoon-17 | ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')) -ForegroundColor Cyan
Write-Host (Get-Location)
'''
    finish = '''
New-Item -ItemType File -Path ($PSCommandPath -replace '\\.ps1$', '.ready') -Force | Out-Null
for ($i=0; $i -lt 60; $i++) { if (Test-Path ($PSCommandPath -replace '\\.ps1$', '.captured')) { break }; Start-Sleep -Milliseconds 500 }
'''
    script.write_text(preamble+content+finish,encoding='utf-8-sig')
    capture(script,ROOT/'evidence'/f'{args.name}-real.png',title)
