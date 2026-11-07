"""Shorten explanations and expose already executed Tasks 3–8 results in the notebook."""
import contextlib
import io
import json
from pathlib import Path
import uuid

ROOT=Path(__file__).resolve().parents[1]
notebook=json.loads((ROOT/'l236050.ipynb').read_text(encoding='utf-8'))

class Factory:
    @staticmethod
    def new_markdown_cell(source):
        return {'cell_type':'markdown','metadata':{},'source':source,'id':uuid.uuid4().hex[:8]}
    @staticmethod
    def new_code_cell(source,execution_count,outputs):
        return {'cell_type':'code','metadata':{},'source':source,'id':uuid.uuid4().hex[:8],
                'execution_count':execution_count,'outputs':outputs}
    @staticmethod
    def new_output(kind,**kwargs):return {'output_type':kind,**kwargs}

class Format:
    v4=Factory
nbformat=Format()
short={
14:'''## 2.1 Input pipeline

I deduplicate by SHA-256 and make stratified 70/15/15 split lists with seed 42. tf.data decodes EXIF-corrected RGB images, pads them to 128 × 128, caches, batches 16 and prefetches; only training is shuffled and randomly augmented.''',
17:'''## 2.2 Baseline CNN

Convolution learns local patterns, batch normalization stabilizes activations, ReLU adds nonlinearity and pooling reduces spatial cost. Global averaging, Dense(64), dropout 0.4 and a sigmoid form a small binary classifier; [0,1] rescaling, weighted binary cross-entropy and Adam(0.001) match the task.''',
20:'''## 2.3 Transfer learning

ImageNet MobileNetV2 (alpha 0.35) uses x/127.5−1 preprocessing and a pooling/dropout/sigmoid head. I first train the head at 0.001, then unfreeze the last block plus Conv_1 at 0.00001 while keeping batch normalization frozen.''',
23:'''## 2.4 Training discipline

Seed 42 and deterministic operations support repeatability. Early stopping and checkpointing monitor validation loss, while ReduceLROnPlateau halves the learning rate after two unimproved epochs; test scores never select checkpoints.''',
26:'''## 2.5 One-time test evaluation

AI is positive; falsely accusing a real image is assigned twice the cost of missing an AI image. I select each threshold from validation cost (2FP+FN)/N, then cache one test prediction pass per fixed model and derive all metrics and plots from it.''',
29:'''## 2.6 Error analysis

I reuse cached baseline predictions to inspect ten mistakes. Each explanation is a visual hypothesis, and the supplied folder labels are unchanged.''',
32:'''## 2.7 Keras Tuner

RandomSearch compares four Fashion-MNIST networks over units and learning rate, then eight VisionGuard configurations over learning rate, dropout and unfrozen layers. All tuning uses training/validation data, and the tuned candidate does not replace the already tested models.''',
34:'''The best toy settings are 128 units and LR 0.001 (validation accuracy 0.8293). VisionGuard's best settings are LR 0.0001, dropout 0.2 and four unfrozen layers (validation AUC 0.8783).

Learning rate has the largest observed grouped mean-AUC range, 0.0113; the small joint search cannot establish causation. Repeated validation selection can overfit noise, so an independent holdout is needed for a fresh final claim. Installing TensorBoard fixed the initial toy dependency failure.'''
}
for index,text in short.items():notebook['cells'][index]['source']=text
notebook['cells']=[c for c in notebook['cells'] if not c['metadata'].get('assignment_completion')]
def add(cell):cell['metadata']['assignment_completion']=True;notebook['cells'].append(cell)
add(nbformat.v4.new_markdown_cell('''## 3 MLflow and DagsHub results

The runnable tracking implementation is `visionguard/experiments.py`; local-toy, remote-toy, project and registry are separate CLI modes. The following cells read completed results without training again or repeating test inference.'''))
code='''from pathlib import Path
import json
import pandas as pd
from IPython.display import display
display(pd.read_csv("artifacts/task3/comparison.csv"))
print(json.dumps(json.loads(Path("model/manifest.json").read_text()), indent=2))
'''
namespace={}
stream=io.StringIO()
# Produce authentic notebook outputs by executing only the saved-result reader.
import IPython.display
shown=[]
original=IPython.display.display
def record_display(value):shown.append(value)
IPython.display.display=record_display
try:
    with contextlib.redirect_stdout(stream):exec(code,namespace)
finally:IPython.display.display=original
outputs=[nbformat.v4.new_output('display_data',data={'text/plain':str(x),'text/html':x.to_html(index=False)}) for x in shown]
outputs.append(nbformat.v4.new_output('stream',name='stdout',text=stream.getvalue()))
add(nbformat.v4.new_code_cell(code,execution_count=1,outputs=outputs))
add(nbformat.v4.new_markdown_cell('''## 4–8 Application and deployment

`visionguard/inference.py` loads the champion once; `visionguard/web.py` validates uploads and calls local or remote inference. `visionguard/database.py` stores history, `compose.yaml` starts web/PostgreSQL, and `.github/workflows` runs tests, Docker builds and the external-network check.

Public API: https://l236050-a2-ops.vercel.app/api/predict. The report contains genuine terminal/UI evidence, Postman results and local Flask cloud-response/history screenshots. Secrets and the local `submission a2` folder are ignored by Git.'''))
code='''import json
from pathlib import Path
proof = json.loads(Path("results/cloud-smoke.json").read_text())
print(json.dumps(proof, indent=2))
'''
with contextlib.redirect_stdout(stream:=io.StringIO()):exec(code,{})
add(nbformat.v4.new_code_cell(code,execution_count=2,outputs=[nbformat.v4.new_output('stream',name='stdout',text=stream.getvalue())]))
(ROOT/'l236050.ipynb').write_text(json.dumps(notebook,ensure_ascii=False,indent=1),encoding='utf-8')
print('Shortened notebook explanations and displayed completed results.')
