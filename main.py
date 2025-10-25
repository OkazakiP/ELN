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

pn.extension('tabulator', 'floatpanel', 'katex', 'mathjax', 'gridstack')


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


FLOATING = False

material = logic.SourceMaterial()
premixture = logic.PreMixture(material)
composition = logic.Composition(material=material, premixture=premixture)
weight = logic.Weight(composition=composition)
weightpremixture = logic.WeightPremixture(premixture=premixture)
work = logic.Work(weight=weight)
workpremixture = logic.WorkPreMixture(weight=weightpremixture)
result = logic.Result(work=work)
result_premixture = logic.ResultPreMixture(workpremixture)

table_material = ViewSourceMaterial(data=material, floating=FLOATING)
table_composition = ViewComposition(
    data=composition, title='02. Composition', floating=FLOATING
)
table_premixture = ViewPremixture(data=premixture, title='03. PreMixture', floating=FLOATING)
table_weight = ViewWeight(data=weight, title='04. Target Weight', floating=FLOATING)
table_weight_premixture = ViewWeightPreMixture(
    data=weightpremixture, title='05. Target PreMixture', floating=FLOATING
)
table_work = ViewWork(data=work, title='06. Log Weight', floating=FLOATING)
table_work_premixture = ViewWorkPreMixture(
    data=workpremixture, title='07. Log PreMixture', floating=FLOATING
)
table_result = ViewResult(data=result, title='08. Result Composition', floating=FLOATING)
table_result_premixture = ViewResultPreMixture(
    data=result_premixture, title='09. Result PreMixture', floating=FLOATING
)

btn_debug = pn.widgets.Button(name='debugger', button_type='danger')
pn.bind(debugger, btn_debug, watch=True)

btn_save = pn.widgets.FileDownload(callback=save, filename='notebook.json')
btn_load = pn.widgets.FileInput(accept='.json', mime_type='text/json')
_ = pn.bind(load, btn_load.param.value, watch=True)

pn.Row(btn_debug, btn_save, btn_load).servable()
#gstack = pn.layout.gridstack.GridStack(mode='override', allow_drag=True, allow_resize=True)
gstack = pn.GridSpec(sizing_mode='stretch_both', max_height=800)
gstack[0, 0] = table_material
gstack[0, 1] = table_composition
gstack[0, 2] = table_premixture
gstack[1, 0] = table_weight
latex = latex = pn.pane.LaTeX(
    r'The LaTeX pane supports two delimiters: $LaTeX$ and \(LaTeX\)', styles={'font-size': '18pt'}
)
gstack[1, 2] = table_weight_premixture
gstack[2, 0] = table_work
gstack[2, 2] = table_work_premixture
gstack[3, 0] = table_result
gstack[3, 2] = table_result_premixture

gstack.servable()