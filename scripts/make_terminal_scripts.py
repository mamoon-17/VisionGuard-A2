"""Prepare real CLI demonstrations. No command output is simulated."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/terminal_scripts'
OUT.mkdir(parents=True,exist_ok=True)
COMMANDS={
'environment':'''Write-Host "`n> Python, package versions and TensorFlow GPU visibility" -ForegroundColor Yellow
& .venv\\Scripts\\python.exe -c "import sys,importlib.metadata as m,tensorflow as tf;print('Python',sys.version.split()[0]);[print(p,m.version(p)) for p in ['tensorflow','keras','numpy','pandas','Pillow','scikit-learn','mlflow','Flask','dvc']];print('GPUs detected:',tf.config.list_physical_devices('GPU'))" 2>evidence/environment-diagnostics.log
Write-Host "`n> git check-ignore .env 'submission a2'" -ForegroundColor Yellow
git check-ignore .env 'submission a2'
''',
'dvc-recovery':'''Set-Location -LiteralPath 'D:\\Mamoon\\Code\\MLOps-A2\\dvc_toy'
Write-Host "`n> git status --short; git log -3 --oneline" -ForegroundColor Yellow
git status --short; git log -3 --oneline
Write-Host "`n> dvc push --all-commits" -ForegroundColor Yellow
& ..\\.venv\\Scripts\\dvc.exe push --all-commits
$before=(Get-FileHash -LiteralPath samples.csv -Algorithm SHA256).Hash
Write-Host "`n> Remove-Item -LiteralPath samples.csv; Test-Path samples.csv" -ForegroundColor Yellow
Remove-Item -LiteralPath (Join-Path (Get-Location) 'samples.csv')
Test-Path -LiteralPath samples.csv
Write-Host "`n> dvc config --local cache.dir .dvc/cache/screenshot-proof; dvc pull" -ForegroundColor Yellow
& ..\\.venv\\Scripts\\dvc.exe config --local cache.dir .dvc/cache/screenshot-proof
& ..\\.venv\\Scripts\\dvc.exe pull
$after=(Get-FileHash -LiteralPath samples.csv -Algorithm SHA256).Hash
Write-Host ('SHA-256 matches after remote recovery: '+($before -eq $after))
Get-Content -LiteralPath samples.csv
''',
'registry-prediction':'''Write-Host "`n> python -m scripts.predict_registered <known AI validation image>" -ForegroundColor Yellow
& .venv\\Scripts\\python.exe -m scripts.predict_registered 'cashbowman/ai-generated-images-vs-real-images/versions/1/AiArtData/AiArtData/memory-palace-by-Louis-Vivin-250_out-1.png' 2>evidence/alias-diagnostics.log
''',
'local-predictions':'''Write-Host "`n> python -m scripts.predict_local" -ForegroundColor Yellow
& .venv\\Scripts\\python.exe -m scripts.predict_local 2>evidence/local-prediction-diagnostics.log
''',
'cnn-summary':'''Write-Host "`n> Load baseline_best.keras and print the actual model summary" -ForegroundColor Yellow
& .venv\\Scripts\\python.exe -c "from tensorflow import keras; keras.models.load_model('artifacts/baseline_best.keras',compile=False).summary(line_length=100)" 2>evidence/summary-diagnostics.log
''',
'compose-status':'''Write-Host "`n> docker compose ps" -ForegroundColor Yellow
docker compose ps
Write-Host "`n> docker compose exec web id" -ForegroundColor Yellow
docker compose exec -T web id
Write-Host "`n> docker compose exec db sh -c 'id; pg_isready'" -ForegroundColor Yellow
docker compose exec -T db sh -c 'id; pg_isready'
Write-Host "`n> docker compose port db 5432 (no published host port)" -ForegroundColor Yellow
docker compose port db 5432
Write-Host "`n> GET http://127.0.0.1:5000/health" -ForegroundColor Yellow
(Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5000/health).Content
''',
'compose-operations':'''Write-Host "`n> docker compose stop; docker compose start; docker compose restart" -ForegroundColor Yellow
docker compose stop
docker compose start
docker compose restart
Write-Host "`n> docker compose ps" -ForegroundColor Yellow
docker compose ps
Write-Host "`n> docker compose logs --tail 2 web db" -ForegroundColor Yellow
docker compose logs --tail 2 web db
''',
'docker-sizes':'''Write-Host "`n> docker image ls l236050_a2_ops" -ForegroundColor Yellow
docker image ls l236050_a2_ops
Write-Host "`n> docker history --format '{{.Size}} {{.CreatedBy}}' l236050_a2_ops:optimized" -ForegroundColor Yellow
docker history --format '{{.Size}} {{.CreatedBy}}' l236050_a2_ops:optimized | ForEach-Object { if($_.Length -gt 112){$_.Substring(0,112)}else{$_} }
''',
}
for name,commands in COMMANDS.items():
    (OUT/f'{name}.commands.ps1').write_text(commands,encoding='utf-8')
print('Prepared',len(COMMANDS),'real command scripts')
