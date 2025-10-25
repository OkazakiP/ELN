import inspect
from io import StringIO
import re
import json
import pandas as pd
import panel as pn

from src import logic
from src.ui import ViewSourceMaterial, ViewPremixture, ViewWeight, ViewWeightPreMixture
from src.ui import ViewComposition, ViewWork, ViewWorkPreMixture
from src.ui import ViewResult, ViewResultPreMixture

pn.extension('tabulator', 'floatpanel', 'katex', 'mathjax')


def list_logic_obj():
    logic_classes = tuple(
        cls for name, cls in inspect.getmembers(logic, inspect.isclass)
    )
    logic_objects = [
        obj for obj in globals().values()
        if isinstance(obj, logic_classes)
    ]
    return logic_objects


def save():
    logic_objects = list_logic_obj()
    f = ',\n'.join(
        ['"' + obj.name + '": ' + obj.data.to_json() for obj in logic_objects]
    )
    f = '{\n    ' + f + '\n}'
    f = StringIO(f)
    f.seek(0)
    return f


def load(value):
    if not value:
        return
    values = json.loads(value)
    pat = r'(?P<class>[^\d]+)\d+'
    values = {re.match(pat, key).group('class'): value for key, value in values.items()}
    logic_objects = list_logic_obj()
    for obj in logic_objects:
        cls = re.match(pat, obj.name).group('class')
        obj.data = pd.read_json(StringIO(json.dumps(values[cls])))


def debugger(event):
    breakpoint()
    pass


material = logic.SourceMaterial()
premixture = logic.PreMixture(material)
composition = logic.Composition(material=material, premixture=premixture)
weight = logic.Weight(composition=composition)
weightpremixture = logic.WeightPremixture(premixture=premixture)
work = logic.Work(weight=weight)
workpremixture = logic.WorkPreMixture(weight=weightpremixture)
result = logic.Result(work=work)
result_premixture = logic.ResultPreMixture(workpremixture)

table_material = ViewSourceMaterial(data=material)
table_composition = ViewComposition(
    data=composition, title='02. Composition'
)
table_premixture = ViewPremixture(data=premixture, title='03. PreMixture')
table_weight = ViewWeight(data=weight, title='04. Target Weight')
table_weight_premixture = ViewWeightPreMixture(
    data=weightpremixture, title='05. Target PreMixture'
)
table_work = ViewWork(data=work, title='06. Log Weight')
table_work_premixture = ViewWorkPreMixture(
    data=workpremixture, title='07. Log PreMixture'
)
table_result = ViewResult(data=result, title='08. Result Composition')
table_result_premixture = ViewResultPreMixture(
    data=result_premixture, title='09. Result PreMixture'
)

btn_debug = pn.widgets.Button(name='debugger', button_type='danger')
pn.bind(debugger, btn_debug, watch=True)

btn_save = pn.widgets.FileDownload(callback=save, filename='notebook.json')
btn_load = pn.widgets.FileInput(accept='.json', mime_type='text/json')
_ = pn.bind(load, btn_load.param.value, watch=True)

pn.Row(btn_debug, btn_save, btn_load).servable()
gspec = pn.GridSpec(sizing_mode='stretch_both', max_height=800)
gspec[0, 0] = table_material
gspec[0, 1] = table_composition
gspec[0, 2] = table_premixture
gspec[1, 0] = table_weight
gspec[1, 2] = table_weight_premixture
gspec[2, 0] = table_work
gspec[2, 2] = table_work_premixture
gspec[3, 0] = table_result
gspec[3, 2] = table_result_premixture

gspec.servable()