from typing import cast, Literal

import numpy as np
import pandas as pd

import param

import panel as pn
from bokeh.models.widgets.tables import NumberEditor, StringEditor, CheckboxEditor
from bokeh.models.widgets.tables import NumberFormatter

from logic import SourceMaterial, Composition, Weight, Work, Result
from logic import PreMixture, WeightPremixture, WorkPreMixture, ResultPreMixture

pn.extension('tabulator', 'floatpanel')



class FloatingView(pn.viewable.Viewer):
    def __init__(
            self,
            title: str = '',
            position:
                Literal['left-top', 'center-top', 'right-top',
                        'left-center', 'center', 'right-center',
                        'left-bottom', 'center-bottom', 'right-bottom'
                        ] = 'left-top',
            **kwargs
        ):
        self.title = title
        self.position = position
        super().__init__(**kwargs)



class ViewSourceMaterial(FloatingView):
    data = param.ClassSelector(class_=SourceMaterial)

    def __panel__(self):
        parameterized = cast(SourceMaterial, self.data)
        parameter = cast(param.Parameter, parameterized.param.data)
        editor = {
            'Concentration': NumberEditor(),
            'Lot': StringEditor(),
        }
        nrows = pn.widgets.IntInput.from_param(
            parameterized.param.nrows, start=1, step=1,
            name='N Material'
        )
        table = pn.widgets.Tabulator.from_param(
            parameter, editors=editor, show_index=False,
            configuration=dict(clipboard=True),
        )
        float_config = dict(
            headerControls=dict(
                close='remove', maximize='remove', minimize='remove'
            )
        )
        return pn.layout.FloatPanel(
            nrows, table,
            name='01. Source Material',
            margin=5,
            config=float_config
        )



class ViewPremixture(FloatingView):
    data = param.ClassSelector(class_=PreMixture)

    def make_editor(self) -> dict:
        parameterized = cast(PreMixture, self.data)
        material = cast(SourceMaterial, parameterized.material)
        material_names = cast(list[str], material.names)
        name = parameterized._name
        editor = {
            col: NumberEditor()
                for col in material_names+[parameterized.total]
        } | {
            name: StringEditor()
        }
        return editor

    @param.depends('data.data', watch=False)
    def make_table(self):
        parameterized = cast(PreMixture, self.data)
        parameter = cast(param.Parameter, parameterized.param.data)
        editor = self.make_editor()
        table = pn.widgets.Tabulator.from_param(
            parameter, editors=editor, show_index=False,
            configuration=dict(clipboard=True),
        )
        return table

    def __panel__(self):
        parameterized = cast(PreMixture, self.data)
        name = parameterized._name
        nrows = pn.widgets.IntInput.from_param(
            parameterized.param.nrows, start=1, step=1,
            name=f'N {name}'
        )
        float_config = dict(
            headerControls=dict(
                close='remove', maximize='remove', minimize='remove'
            )
        )
        return pn.layout.FloatPanel(
            nrows, self.make_table,
            name=self.title, margin=20, config=float_config,
            position=self.position, contained=True,
        )



class ViewComposition(ViewPremixture):
    data = param.ClassSelector(class_=Composition)

    def make_editor(self) -> dict:
        parameterized = cast(Composition, self.data)
        material = cast(SourceMaterial, parameterized.material)
        material_names = cast(list[str], material.names)
        premixture = cast(PreMixture, parameterized.premixture)
        premixture_names = cast(list[str], premixture.names)
        name = parameterized._name
        editor = {
            col: NumberEditor()
                for col in material_names+[parameterized.total]
        } | {
            name: StringEditor()
        } | {
            col: CheckboxEditor()
                for col in premixture_names
        }
        return editor



class ViewWeight(FloatingView):
    data = param.ClassSelector(class_=Weight)

    @param.depends('data.digit', watch=False)
    def make_table(self) -> pn.widgets.Tabulator:
        weight = cast(Weight, self.data)
        digit = cast(int, weight.digit)
        parameter = cast(param.Parameter, weight.param.data)
        data = cast(pd.DataFrame, weight.data)
        composition = cast(Composition, weight.composition)
        material = cast(SourceMaterial, composition.material)
        premixture = cast(PreMixture, composition.premixture)
        material_names = cast(list[str], material.names)
        preixture_names = cast(list[str], premixture.names)
        formatters = {
            col: NumberFormatter(format=f'0.{str(0)*digit}')
            for col in material_names+preixture_names+['Solvent']
        }
        editors = {col: None for col in data.columns}
        table = pn.widgets.Tabulator.from_param(
            parameter, show_index=False,
            configuration=dict(clipboard=True),
            formatters=formatters, editors=editors,
        )
        return table

    def __panel__(self):
        weight = cast(Weight, self.data)
        digit = pn.widgets.IntInput.from_param(
            weight.param.digit,
            name='N Digit',
        )
        float_config = dict(
            headerControls=dict(
                close='remove', maximize='remove', minimize='remove'
            )
        )
        return pn.layout.FloatPanel(
            digit, self.make_table,
            name=self.title, margin=20, config=float_config,
            position=self.position, contained=True,
        )



class ViewWeightPreMixture(ViewWeight):
    data = param.ClassSelector(class_=WeightPremixture)

    @param.depends('data.digit', watch=False)
    def make_table(self) -> pn.widgets.Tabulator: # type: ignore[override]
        weight = cast(WeightPremixture, self.data)
        digit = cast(int, weight.digit)
        parameter = cast(param.Parameter, weight.param.data)
        data = cast(pd.DataFrame, weight.data)
        premixture = cast(PreMixture, weight.premixture)
        material = cast(SourceMaterial, premixture.material)
        material_names = cast(list[str], material.names)
        formatters = {
            col: NumberFormatter(format=f'0.{str(0)*digit}')
            for col in material_names+['Solvent']
        }
        editors = {col: None for col in data.columns}
        table = pn.widgets.Tabulator.from_param(
            parameter, show_index=False,
            configuration=dict(clipboard=True),
            formatters=formatters, editors=editors,
        )
        return table



class ViewWork(FloatingView):
    data = param.ClassSelector(class_=Work)
    threshold = param.Number(default=0.01)

    def validate(self, value, target):
        try:
            res = abs(value/target - 1) < self.threshold
            res = 'blue' if res else 'red'
        except ZeroDivisionError:
            res = 'blue' if np.isnan(value) else 'red'
        except TypeError:
            res = 'black'
        return res

    def coloring(self, s):
        work = cast(Work, self.data)
        weight = cast(Weight, work.weight)
        weight_data = cast(pd.DataFrame, weight.data)
        color = [
            f'color: {self.validate(value, target)}'
            for value, target in zip(s, weight_data[s.name])
        ]
        return color

    @param.depends('data.data', 'threshold', watch=False)
    def make_table(self) -> pn.widgets.Tabulator:
        work = cast(Work, self.data)
        work_data = cast(pd.DataFrame, work.data)
        parameter = work.param.data
        editor = {
            col: NumberEditor()
                for col in work_data.columns if col != 'Composition'
        }
        table = pn.widgets.Tabulator.from_param(
            parameter, editors=editor, show_index=False,
            configuration=dict(placeholder='empty'),
        )
        cast(pd.DataFrame, table).style.apply(self.coloring)
        return table

    def __panel__(self):
        threshold = pn.widgets.NumberInput.from_param(
            self.param.threshold, name='Validation'
        )
        float_config = dict(
            headerControls=dict(
                close='remove', maximize='remove', minimize='remove'
            )
        )
        return pn.layout.FloatPanel(
            threshold, self.make_table,
            name=self.title, margin=20, config=float_config,
            position=self.position, contained=True,
        )



class ViewWorkPreMixture(ViewWork):
    data = param.ClassSelector(class_=WorkPreMixture)
    threshold = param.Number(default=0.01)

    @param.depends('data.data', 'threshold', watch=False)
    def make_table(self) -> pn.widgets.Tabulator: # type: ignore[override]
        work = cast(Work, self.data)
        work_data = cast(pd.DataFrame, work.data)
        parameter = work.param.data
        editor = {
            col: NumberEditor()
                for col in work_data.columns if col != 'Premixture'
        }
        table = pn.widgets.Tabulator.from_param(
            parameter, editors=editor, show_index=False,
            configuration=dict(placeholder='empty'),
        )
        cast(pd.DataFrame, table).style.apply(self.coloring)
        return table



class ViewResult(FloatingView):
    data = param.ClassSelector(class_=Result)

    @param.depends('data.data', watch=False)
    def make_table(self):
        result = cast(Result, self.data)
        data = cast(param.Parameter, result.param.data)
        result_data = cast(pd.DataFrame, result.data)
        editor = {key: None for key in result_data.columns}
        table = pn.widgets.Tabulator.from_param(
            data, editors=editor, show_index=False,
        )
        return table

    def __panel__(self):
        float_config = dict(
            headerControls=dict(
                close='remove', maximize='remove', minimize='remove'
            )
        )
        return pn.layout.FloatPanel(
            self.make_table,
            name=self.title, margin=20, config=float_config,
            position=self.position, contained=True,
        )



class ViewResultPreMixture(ViewResult):
    data = param.ClassSelector(class_=ResultPreMixture)