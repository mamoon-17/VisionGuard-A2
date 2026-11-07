"""Build the concise hand-in report from executed results and genuine captures.

Run using the bundled document runtime, not the ML virtual environment.
"""
import csv
import json
import subprocess
from html.parser import HTMLParser
from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence'
ASSETS=E/'report-assets';ASSETS.mkdir(exist_ok=True)
if not all((ASSETS/(r+'.png')).exists() for r in ['rId6','rId8','rId9','rId10']):
    OLD=Document(ROOT/'Report.docx')
    for relationship in ['rId6','rId8','rId9','rId10']:
        part=OLD.part.related_parts[relationship]
        (ASSETS/(relationship+'.png')).write_bytes(part.blob)
# These user-requested crops remove the superseded remote setup and installation noise.
for name,bottom in [('rId6.png',260),('rId8.png',256)]:
    source=ASSETS/name
    image=Image.open(source)
    if image.height>bottom:image.crop((0,0,image.width,bottom)).save(source)
NOTEBOOK=json.loads((ROOT/'l236050.ipynb').read_text(encoding='utf-8'))
PREVIEW=Path(r'C:\Users\Mamoon\.codex\visualizations\2026\11\01\01a197f8-1bb0-74b2-a660-e20beaf0ddfb')
CODE_COMMIT=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
DOC=Document()
section=DOC.sections[0]
section.page_width=Inches(8.5);section.page_height=Inches(11)
section.top_margin=section.bottom_margin=Inches(.65)
section.left_margin=section.right_margin=Inches(.7)
for name in ['Normal','Body Text']:
    style=DOC.styles[name];style.font.name='Calibri';style.font.size=Pt(11)
    style.paragraph_format.space_after=Pt(5)
    style.paragraph_format.line_spacing=1.05
for name,size in [('Title',25),('Heading 1',17),('Heading 2',12)]:
    DOC.styles[name].font.name='Calibri';DOC.styles[name].font.size=Pt(size)
    DOC.styles[name].font.color.rgb=RGBColor.from_string('000000')
    DOC.styles[name].paragraph_format.keep_with_next=True
footer=section.footer.paragraphs[0]
footer.alignment=2
footer.add_run('l236050 A2 Ops  |  ')
field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)
for run in footer.runs:run.font.size=Pt(9)

def p(text,style=None):
    return DOC.add_paragraph(text,style)

def h(text,level=2):
    element=DOC.add_heading(text,level)
    if level==1:element.paragraph_format.page_break_before=True
    return element

FIGURE=0
def figure(path,caption,height=4.25):
    global FIGURE
    path=Path(path)
    if not path.exists():raise FileNotFoundError(path)
    picture=Image.open(path)
    if picture.width<300 or picture.height<45:raise ValueError(f'Invalid screenshot dimensions: {path}')
    if path.name.endswith('-real.png'):
        body=picture.convert('RGB').crop((8,32,picture.width-24,picture.height-8))
        mask=body.convert('L').point(lambda value:255 if value>65 else 0)
        bounds=mask.getbbox()
        if bounds:
            picture=picture.crop((0,0,min(picture.width,bounds[2]+32),min(picture.height,bounds[3]+56)))
            cropped=ASSETS/('crop-'+path.name);picture.save(cropped);path=cropped
    elif path.name in ['app-health.png','cloud-health.png']:
        picture=picture.crop((0,0,800,80))
        cropped=ASSETS/('crop-'+path.name);picture.save(cropped);path=cropped
    # Only crop unused bottom space; never synthesize or replace screenshot contents.
    width=min(7.1,height*picture.width/picture.height)
    paragraph=DOC.add_paragraph();paragraph.paragraph_format.keep_with_next=True
    paragraph.add_run().add_picture(str(path),width=Inches(width))
    FIGURE+=1
    caption_p=p(f'Figure {FIGURE}. {caption}')
    for run in caption_p.runs:run.italic=True;run.font.size=Pt(9)
    return FIGURE

def table(headers,rows,widths=None):
    t=DOC.add_table(rows=1,cols=len(headers));t.autofit=False
    weights=widths or [max(6,min(25,max(len(str(r[i])) for r in [headers,*rows]))) for i in range(len(headers))]
    for c,w in zip(t.columns,weights):c.width=Inches(7.1*w/sum(weights))
    for number,values in enumerate([headers,*rows]):
        cells=t.rows[0].cells if number==0 else t.add_row().cells
        for cell,w,value in zip(cells,weights,values):
            cell.width=Inches(7.1*w/sum(weights));cell.text=str(value)
            properties=cell._tc.get_or_add_tcPr()
            borders=OxmlElement('w:tcBorders')
            for edge in ['top','left','bottom','right']:
                item=OxmlElement('w:'+edge)
                for key,val in [('val','single'),('sz','4'),('color','D9D9D9')]:item.set(qn('w:'+key),val)
                borders.append(item)
            properties.append(borders)
            shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'DCE6EF' if number==0 else ('F5F7F9' if number%2==0 else 'FFFFFF'));properties.append(shade)
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_after=Pt(3);paragraph.paragraph_format.space_before=Pt(3)
                if len(rows)<=10:paragraph.paragraph_format.keep_with_next=number<len(rows)
                for run in paragraph.runs:run.font.size=Pt(9);run.bold=number==0
        if number==0:
            repeat=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(repeat)
    p('')
    return t

def csv_table(path,columns,labels=None):
    rows=list(csv.DictReader(Path(path).open(encoding='utf-8')))
    def fmt(value):
        try:
            x=float(value)
            return str(int(x)) if x.is_integer() else f'{x:.4g}'
        except (ValueError,TypeError):return value
    table(labels or columns,[[fmt(row[c]) for c in columns] for row in rows])

class Parser(HTMLParser):
    def __init__(self):super().__init__();self.rows=[];self.row=[];self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='tr':self.row=[]
        if tag in ['td','th']:self.cell=[]
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ['td','th'] and self.cell is not None:self.row.append(''.join(self.cell).strip());self.cell=None
        if tag=='tr' and self.row:self.rows.append(self.row)

def notebook_tables(cell):
    result=[]
    for output in NOTEBOOK['cells'][cell].get('outputs',[]):
        html=output.get('data',{}).get('text/html')
        if html:
            parser=Parser();parser.feed(''.join(html));result.append(parser.rows)
    return result

p('VisionGuard assignment report','Title')
p('l236050 A2 Ops')
p('Name: Mamoon  |  Roll number: l236050  |  Completed: 8 November 2026')
p('I built, tracked and deployed a real versus AI image classifier. This report presents the required results, genuine screenshots and reproduction steps; the model remains an experimental screening tool.')
table(['Submission link','Location'],[
 ['GitHub and CI','https://github.com/mamoon-17/VisionGuard-A2'],
 ['DagsHub data and registry','https://dagshub.com/mamoon-17/VisionGuard-A2'],
 ['Public inference API','https://l236050-a2-ops.vercel.app/api/predict'],
 ['Public health check','https://l236050-a2-ops.vercel.app/health'],
 ['Graded source commit',CODE_COMMIT]],widths=[1,3])
p('AI disclosure: Codex assisted with implementation, experiments, troubleshooting, screenshots and report editing. Keras, MLflow, DVC, Docker and Vercel documentation informed the implementation. No accuracy or screenshot evidence was fabricated.')
p('The user-created repositories retain the supplied VisionGuard-A2 name; MLflow, registry, Docker and cloud resources use the roll-number project name. Credentials and the local submission folder are Git-ignored.')

h('Task 1 Data understanding and versioning',1)
h('1.1 Environment')
p('I used Python 3.12.10 in an isolated .venv. Figure 1 records the installed versions; TensorFlow detects no GPU, so all experiments use CPU.')
figure(E/'environment-real.png','Actual PowerShell version and GPU checks, with proof that .env and submission a2 are ignored.',3.45)
h('1.2 Dataset audit')
p('The notebook walks both class folders, opens each image and records dimensions, mode, format, bytes and SHA-256. It found no unreadable images and one exact duplicate, which I excluded before splitting.')
table(['Class','Images','Unreadable','Extra duplicates'],[['AI-generated',539,0,1],['Real',436,0,0]])
table(['Class and measurement','Minimum','Median','Maximum'],[
 ['AI width px',225,1024,6000],['Real width px',183,920,8495],['AI height px',135,800,4001],['Real height px',158,720,7091],
 ['AI file bytes',11738,199760,5626183],['Real file bytes',11311,144840,10195352]])
p('AiArtData/image33.jpg and image34.jpg have the same content hash. The retained 974 images form disjoint stratified lists: 681 training, 146 validation and 147 test images; hash-overlap checks prevent leakage.')
h('1.3 Visual EDA')
eda=[
 ('Sample grid selected with seed 42.','Both classes contain varied subjects and styles. Artwork also occurs in the Real class, so style alone cannot establish image origin.'),
 ('Image width by class with shared bins.','Widths are right-skewed, with medians of 1024 px for AI and 920 px for Real. Common resizing is necessary, and native size may be a collection bias.'),
 ('Image height by class with shared bins.','Median heights are 800 px for AI and 720 px for Real. The Real class has a longer upper tail, so padding preserves proportions across varied shapes.'),
 ('File size by class in MiB with shared bins.','Median sizes are approximately 0.19 MiB for AI and 0.14 MiB for Real. A few large files dominate the tail; compression and format can explain part of this difference.')]
for i,(caption,interpretation) in enumerate(eda,1):
    figure(PREVIEW/f'eda-preview/figure-{i}.png',caption,3.65);p(interpretation)
h('1.4 Git and DVC')
p('Git records code and small DVC pointers; a pointer holds the content hash, path and size metadata. Image binaries remain in DVC storage because repeated large binaries inflate Git history.')
figure(ASSETS/'rId6.png','User-provided initial Git commit, cropped to exclude the superseded GitHub setup.',2.25)
figure(ASSETS/'rId8.png','User-provided successful Git push to the DagsHub repository.',2.8)
figure(ASSETS/'rId9.png','User-provided DagsHub storage configuration and dataset/artifact tracking.',3.1)
figure(ASSETS/'rId10.png','User-provided successful DVC push; credential-entry lines were cropped out.',1.3)
p('In an empty dvc_toy repository I committed CSV versions 1 and 2, pushed both to DagsHub, then restored the v1 pointer with dvc checkout. The dvc-toy branch and tags retain commits 1ccff4c, a77caee and rollback 4c9ec7d.')
figure(E/'dvc-versions-real.png','Actual toy Git history, both DVC pointers and the restored two-row CSV.',3.2)
p('I deleted only samples.csv, configured a fresh empty cache and ran dvc pull. The remote-restored file had the same SHA-256 as the original, proving recovery from storage rather than a remaining workspace copy.')
figure(E/'dvc-recovery-real.png','Actual deletion, remote fetch and hash-verified recovery.',3.8)

h('Task 2 Model development',1)
h('2.1 Input pipeline')
p('The tf.data pipeline reads split CSVs, decodes with Pillow, applies EXIF orientation and RGB conversion, resizes with padding to 128 × 128, caches, batches 16 and prefetches. Training alone is shuffled and augmented; padding preserves aspect ratio, while 128 px keeps CPU training practical.')
figure(PREVIEW/'task2_preview/2.1-1-1.png','One augmented training batch; validation and test images receive no random transforms.',3.5)
h('2.2 Baseline CNN')
p('Three convolution blocks learn visual patterns; normalization stabilizes activations, ReLU adds nonlinearity and pooling reduces spatial cost. Global averaging and a 64-unit dense layer combine features, dropout 0.4 regularizes them, and one sigmoid predicts AI probability.')
p('Internal rescaling maps pixels to [0,1]. Binary cross-entropy matches binary labels; Adam at 0.001 optimizes the weights, and accuracy, precision, recall and ROC-AUC expose different errors; class weights address imbalance.')
layers=notebook_tables(18)[0]
layers=[row[1:] for row in layers]
table(layers[0],layers[1:],widths=[2.3,2.1,2.2,1.3])
figure(E/'cnn-summary-real.png','Actual Keras baseline summary; the table gives each layer shape and parameter count.',3.8)
h('2.3 Transfer learning')
p('I loaded ImageNet MobileNetV2 without its classifier, with width multiplier 0.35 and a pooling/dropout/sigmoid head. Rescaling x / 127.5 − 1 matches its pretrained [-1,1] inputs.')
table(['Stage','Trainable weighted layers','Learning rate'],[
 ['Frozen backbone','ai_probability (1281 parameters)','0.001'],
 ['Final block fine-tune','block_16_expand, block_16_depthwise, block_16_project, Conv_1, ai_probability','0.00001']],widths=[1.5,4,1])
p('Fine-tuning begins from the best frozen checkpoint with a 100 times smaller learning rate. Batch normalization stays frozen to avoid unstable moving statistics on this small dataset.')
figure(PREVIEW/'task2_preview/2.3-1-1.png','Frozen-backbone training curves, best validation-loss epoch marked.',3.1)
figure(PREVIEW/'task2_preview/2.3-1-2.png','Last-block fine-tuning curves, best validation-loss epoch marked.',3.1)
h('2.4 Training discipline')
p('Seed 42 and deterministic TensorFlow operations make runs reproducible. EarlyStopping and ModelCheckpoint monitor validation loss; ReduceLROnPlateau halves the rate after two unimproved epochs, and no callback uses test results.')
epochs=json.loads((ROOT/'artifacts/best_epochs.json').read_text())
table(['Stage','Completed epochs','Best epoch','Best val loss'],[[x['stage'],x['epochs_completed'],x['best_epoch'],f"{x['best_validation_loss']:.4f}"] for x in epochs])
figure(PREVIEW/'task2_preview/2.4-1-1.png','Baseline curves with best epoch 20 marked.',3.1)
p('Frozen MobileNetV2 was retained because its best validation loss, 0.4755, was lower than the fine-tuned model’s 0.4860. Fine-tuning therefore did not automatically replace the better checkpoint.')
h('2.5 Evaluation')
p('AI is the positive class. I value a real photo falsely called fake more severely, so validation thresholds minimize (2FP + FN) / N; all test metrics and plots reuse one cached prediction pass per fixed model.')
csv_table(ROOT/'artifacts/test_metrics.csv',['model','threshold','accuracy','precision_AI','recall_AI','F1_AI','ROC_AUC'],['Model','Threshold','Accuracy','Precision','Recall','F1','AUC'])
figure(PREVIEW/'task2_preview/2.5-1-1.png','Confusion matrices at validation-selected thresholds.',3.2)
figure(PREVIEW/'task2_preview/2.5-1-2.png','ROC curves from the same cached test probabilities.',3.2)
p('MobileNetV2 reached 68.71% accuracy and AUC 0.7761 on 147 test images. Its conservative threshold produced 5 real-to-AI errors but missed 41 AI images, so the output is not proof of authenticity.')
h('2.6 Error analysis')
p('These ten baseline mistakes reuse the cached test predictions. Each explanation is a visual hypothesis; folder labels remain unchanged.')
for i in [1,2]:figure(PREVIEW/f'task2_preview/report-errors-{i}.png',f'Misclassified baseline test examples {(i-1)*5+1}–{i*5}, with ground truth and prediction.',3.3)
table(['Example','Hypothesis'],[
 [1,'Saturated mountains and smooth lighting resemble synthetic imagery.'],[2,'Polished stock-photo lighting and blue background resemble training AI images.'],
 [3,'Flat cartoon outlines overlap with human illustration styles.'],[4,'Vivid abstract painting resembles generated artwork.'],[5,'Side-by-side portrait boundaries and different backgrounds resemble compositing.'],
 [6,'Smooth autumn reflection and ai-generative in a Real filename suggest possible label noise.'],[7,'Mixed colour and monochrome portrait textures resemble generation artifacts.'],
 [8,'A Real-labelled cartoon has smooth gradients and simplified anatomy.'],[9,'A photographic face may dominate the small cartoon in an AI portrait.'],[10,'Flat pop-art colours and repetition are ambiguous.']],widths=[.7,6])
h('2.7 Keras Tuner')
p('RandomSearch tested learning rate and hidden units on Fashion-MNIST, then eight VisionGuard combinations of learning rate, dropout and unfrozen layers. Each VisionGuard trial starts from the same frozen checkpoint and uses only training/validation data.')
csv_table(ROOT/'artifacts/toy_tuner_results.csv',['trial','units','learning_rate','validation_score'],['Toy trial','Units','LR','Val accuracy'])
csv_table(ROOT/'artifacts/visionguard_tuner_results.csv',['trial','dropout','unfrozen_layers','learning_rate','validation_score'],['Trial','Dropout','Unfrozen','LR','Val AUC'])
p('The best settings were LR 0.0001, dropout 0.2 and four unfrozen layers, with validation AUC 0.8783. Learning rate had the largest grouped mean-AUC range (0.0113), but eight jointly varied trials do not prove causation; repeated selection can overfit validation noise.')
p('The first toy attempt lacked TensorBoard; installing it resolved the tuner dependency. This validation-only candidate did not replace the already tested Task 2 models.')

h('Task 3 Experiment tracking',1)
h('3.1 Local MLflow lab')
p('Two 64-unit Fashion-MNIST networks differ only in learning rate; both log parameters, epoch metrics, a curve and a standard MLflow model artifact. Validation accuracy was 0.8080 at LR 0.001 and 0.6973 at LR 0.0001.')
for name,caption in [('local-toy-fast','Local toy run at learning rate 0.001.'),('local-toy-slow','Local toy run at learning rate 0.0001.'),('mlflow-local-compare','Actual local MLflow comparison of both completed runs.')]:figure(E/(name+'.png'),caption,3.65)
table(['Term','Meaning'],[['Experiment','A group of related training attempts.'],['Run','One recorded attempt with its results.'],['Parameter','An input setting such as learning rate.'],['Metric','A measured number, possibly recorded each epoch.'],['Artifact','A saved file such as a plot or model.'],['Tag','Searchable context such as seed or Git revision.']],widths=[1,4])
h('3.2 DagsHub setup')
p('The DagsHub project is connected to GitHub through the CI mirror job. .env supplies the tracking URI, username and token; Figure 1 proves it is ignored, and the remote toy run confirms authenticated tracking.')
figure(E/'remote-toy.png','Actual toy run in the DagsHub-hosted MLflow project.',3.65)
h('3.3 Manual and automatic logging')
p('A manual callback explicitly records each epoch; TensorFlow autologging also captures fit/optimizer settings, summaries and metrics. Both require explicit Git/DVC/seed tags, final test metrics and product-specific artifacts.')
figure(E/'remote-manual.png','Manual run parameters, metrics and provenance on DagsHub.',4.25)
figure(E/'remote-autolog.png','Automatically instrumented TensorFlow run with manually supplied provenance.',4.25)
for name in ['remote-manual-curves','remote-autolog-curves']:
    figure(E/(name+'.png'),'Actual MLflow metric-history view for '+('manual' if 'manual-' in name else 'automatic')+' logging.',3.6)
p('Loaded Keras models initially bypassed the fit patch, and an implicit batch_size=None conflicted with the recorded 16. Enabling autologging after deserialization and passing batch_size=16 fixed it; deterministic replay matched saved histories exactly and did not repeat test inference.')
h('3.4 Run artifacts')
p('Each run contains confusion/ROC figures, train/validation/test CSVs, the package list and a standard MLflow Keras model directory. These files capture the exact split and environment beyond the scalar metrics.')
figure(E/'remote-artifacts.png','DagsHub artifact browser with evidence, model, splits and package list.',3.65)
h('3.5 Six controlled experiments')
p('Every run changes one factor from the same warm-start reference. Selection minimizes validation cost, then maximizes validation AUC; test columns are descriptive and do not choose the champion.')
csv_table(ROOT/'artifacts/task3/comparison.csv',['name','learning_rate','dropout','augmentation','unfrozen_layers','validation_cost','validation_ROC_AUC'],['Run','LR','Drop','Aug','Unfr','Val cost','Val AUC'])
figure(E/'mlflow-six-compare.png','Actual DagsHub comparison of all six runs; the table above gives the selection metrics.',3.9)
p('Unfreezing four layers had the lowest validation cost (0.2397) and highest validation AUC (0.8729), so it became champion. Its test accuracy was 0.7415 and AUC 0.8260; this tracking exercise reuses the existing holdout and is not a fresh independent benchmark.')
h('3.6 Registry and serving handoff')
p('Version 1 stores the runner-up; version 2 has alias champion. The separate predict_registered script resolves that alias and its stored threshold; DVC provisions the local champion once, so serving never queries DagsHub per request.')
figure(E/'registry.png','Two registered DagsHub versions and the champion alias.',3.55)
figure(E/'registry-prediction-real.png','Real terminal output loading models:/l236050_A2_Ops@champion and predicting an image.',3.0)

h('Task 4 Flask web application',1)
h('4.1 Inference module')
p('Predictor loads the local champion once per process and serializes model calls with a lock. EXIF/RGB conversion, first-frame selection and padded 128 px resizing match training; repeated model loading would add disk and initialization cost to every upload.')
figure(E/'local-predictions-real.png','Two known validation images classified with one loaded local champion.',2.75)
h('4.2 Routes and validation')
p('Upload, result, history and health routes sanitize filenames, validate allowed extensions against decoded contents and enforce a 5 MiB local request limit. Upload bytes stay in memory; friendly error pages reject wrong type, corrupt image and oversized request.')
for name,caption in [('type','Unsupported extension rejected.'),('decode','Undecodable image rejected.'),('size','Oversized request rejected.')]:figure(E/f'app-error-{name}.png',caption,2.85)
h('4.3 HTML and CSS')
p('The upload page leads to a label, chosen-class probability and authenticity caveat. The menu opens database-backed history; confidence is the model’s probability, not a calibrated guarantee.')
figure(E/'app-upload.png','Actual local HTML upload page.',3.1)
figure(E/'app-result-1.png','Actual result with model version, probability, threshold and caveat.',3.6)
h('4.4 Production configuration')
p('Environment variables configure the model path, threshold, database and API key. Debug mode is off; Waitress serves Windows locally and Gunicorn serves Docker, avoiding development reloader duplication and exposed debug tracebacks.')
figure(E/'app-health.png','Local health endpoint confirms configuration and model version.',1.7)

h('Task 5 Database trail',1)
p('SQLAlchemy writes each prediction and validation rejection to SQLite locally and PostgreSQL in Compose. Successful rows contain UTC time, sanitized filename, content hash, label, confidence, AI probability, model version and latency; images are never retained.')
p('The History menu queries the latest 100 records. A restart-persistence test confirms records survive a new app instance; PostgreSQL additionally uses a persistent named Docker volume.')
figure(E/'app-history.png','Actual database-backed history including successful and rejected requests.',4.45)

h('Task 6 Containers and CI',1)
h('6.1 Docker warm up')
p('I ran ready-made Nginx with a mapped local port and read-only HTML volume, fetched its page, read logs, opened a shell and listed it. I then removed only the lab container and its extra image tag.')
figure(E/'docker-warmup-real.png','Actual run, port/volume mapping, HTTP request, shell, logs and container listing.',4.1)
figure(E/'docker-cleanup-real.png','Actual lab container and image-tag removal, followed by empty listings.',2.7)
table(['Term','Meaning'],[['Image','A packaged filesystem and process configuration.'],['Container','A running or stopped instance of an image.'],['Layer','A reusable filesystem change in an image.'],['Volume','Storage whose lifetime can outlast a container.'],['Port mapping','A host address/port forwarded to a container port.']],widths=[1,4])
h('6.2 Dockerfile')
p('Dockerfile uses python:3.12-slim and installs CPU-only TensorFlow with no pip cache. Dependencies precede source copies so ordinary source edits reuse that expensive layer; .dockerignore excludes credentials, datasets and local outputs, and UID 10001 runs the web process.')
p('Source: https://github.com/mamoon-17/VisionGuard-A2/blob/main/Dockerfile. A health check calls /health; Figure below also proves the non-root user.')
figure(E/'compose-status-real.png','Actual healthy services, web UID 10001, database readiness and no host database port binding.',3.8)
h('6.3 Compose stack')
p('compose.yaml connects web to PostgreSQL at service name db:5432, starts web only after pg_isready, and publishes only web on 127.0.0.1:5000. Passwords come from ignored .env; a named history_data volume persists records, and ./model is mounted read-only for independent model updates.')
p('Source: https://github.com/mamoon-17/VisionGuard-A2/blob/main/compose.yaml. .env.example documents every required setting without real secrets; the database port has a null external binding in the status evidence.')
h('6.4 Image analysis')
table(['Docker image listing','Before','After'],[['Docker Desktop reported size','4.37 GB','2.23 GB']])
p('The same docker image ls measurement falls by about 49% after using slim and removing pip cache. The optimized dependency layer is largest at 1.67 GB; TensorFlow dominates, while code layers are tiny. Registry-compressed sizes differ from these local image-list figures.')
figure(E/'docker-sizes-real.png','Actual before/after image listing and optimized layer history.',3.65)
h('6.5 Operations and troubleshooting')
p('I stopped, started and restarted both services, then read their logs and opened shells. A one-off web container with a missing MODEL_PATH failed at startup; the log named that path, and using the original read-only model mount restored /health.')
figure(E/'compose-operations-real.png','Actual Compose lifecycle and logs for both services.',3.4)
figure(E/'docker-failure-real.png','Actual missing-model failure, diagnosis and successful original-service health check.',3.8)
h('6.6 GitHub Actions')
p('The throwaway repository runs pytest on Python 3.11 and 3.12: the wrong 2+2 expectation fails, then correcting it passes. Project CI installs dependencies, runs Ruff and nine tests, builds Docker and mirrors successful main builds to DagsHub; README contains the live badge.')
figure(E/'ci-red-green.png','Actual red then green GitHub Actions lab runs.',3.7)
figure(E/'ci-project-green.png','Actual successful project CI and DagsHub mirror jobs.',3.8)
p('DAGSHUB_TOKEN and VISIONGUARD_API_KEY are GitHub repository Actions secrets injected through environment variables. Committing them in YAML would expose credentials to every repository reader.')

h('Task 7 Public API deployment',1)
p('The model API runs on Vercel; the Flask UI and persistent history remain local. Standard Python functions are too small for TensorFlow, so I enabled Vercel’s current 5 GB large-function beta; the deployment is stateless and uses no cloud SQLite file.')
table(['Step','Action and reason'],[
 [1,'python scripts/prepare_deployment.py copies the fixed champion, manifest and inference module into deployment/vercel.'],
 [2,'vercel login authenticates the CLI; vercel link --yes --project l236050-a2-ops selects the cloud project.'],
 [3,'python scripts/deploy_vercel.py sends API_KEY through stdin, enables VERCEL_SUPPORT_LARGE_FUNCTIONS and runs vercel deploy --prod --yes.'],
 [4,'pyproject.toml pins Python 3.12 and runtime dependencies; vercel.json includes model files and permits up to 300 seconds.'],
 [5,'GET /health checks deployment; Postman/Newman sends multipart image bytes to /api/predict with X-API-Key.'],
 [6,'A GitHub-hosted Ubuntu workflow sends an authenticated prediction from another network and records its JSON response.']],widths=[.6,6])
p('API: https://l236050-a2-ops.vercel.app/api/predict. HTTPS and an API key protect inference; the API limits multipart requests to 4 MB, below Vercel’s 4.5 MB ceiling, and loads the model once in each warm worker.')
figure(E/'vercel-deployment-real.png','Actual Vercel deployment inspection and live health check.',3.8)
figure(E/'postman-real.png','Actual Postman Newman collection run against the public API.',3.8)
figure(E/'external-network-real.png','Actual GitHub-hosted external-network API test and recorded result.',3.8)
p('The first deployment omitted dependencies because Vercel selected pyproject.toml; declaring them there fixed the runtime failure. The large-function beta succeeded, so a separate paid inference server was unnecessary for this coursework deployment.')
p('Postman passed all six transport/schema assertions. Its AI-labelled sample returned Real at pAI 0.7186, below the conservative 0.7481 threshold; a successful API request does not guarantee a correct classification.')
p('Reference: https://vercel.com/changelog/vercel-functions-can-now-be-up-to-5-gb-in-package-size-7yAwSyCig0IQDXUIDistvS/eadf06d6c3 and https://vercel.com/docs/functions/limitations. No managed cloud database is needed because request history is stored by the local Flask application.')

h('Task 8 Flask and API integration',1)
p('REMOTE_INFERENCE_URL points local Flask to the hosted /api/predict; requests sends validated multipart bytes with the API key and explicit timeouts. Flask renders the returned model version and decision, then saves the response to local SQLite without saving the image.')
figure(E/'cloud-result-0.png','Local Flask displaying the cloud response for a real-labelled validation image.',3.7)
figure(E/'cloud-result-1.png','Local Flask displaying the cloud response for an AI-labelled validation image.',3.7)
figure(E/'cloud-health.png','Local UI health confirms remote inference mode.',1.65)
figure(E/'cloud-history.png','History menu with actual cloud responses recorded in the local database.',4.1)
p('Both uploads received responses from the public champion endpoint and appear in history. Validation and network errors have friendly pages; model mistakes remain possible even when API transport and logging succeed.')

DOC.core_properties.title='VisionGuard assignment report'
DOC.core_properties.author='Mamoon'
DOC.core_properties.subject='l236050 A2 Ops reproducible model development and deployment'
for style in DOC.styles:
    for border in list(style.element.xpath('.//w:pBdr')):border.getparent().remove(border)
for border in list(DOC.element.xpath('.//w:pBdr')):border.getparent().remove(border)
target=E/'Report-concise.docx'
DOC.save(target)
print('Built',target,'figures',FIGURE,'source commit',CODE_COMMIT)
