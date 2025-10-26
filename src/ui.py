from typing import cast, Literal

import numpy as np
import pandas as pd

import param

import panel as pn
from bokeh.models.widgets.tables import NumberEditor, StringEditor, CheckboxEditor
from bokeh.models.widgets.tables import NumberFormatter

from src.logic import SourceMaterial, Composition, Weight, Work, Result
from src.logic import PreMixture, WeightPremixture, WorkPreMixture, ResultPreMixture



class FloatingView(pn.viewable.Viewer):
    """Mixin class for (floating) tables.

    Attributes
    ----------
    title: str
        The title of the table.
    position: str
        Initial position where the table is rendered.
    floating: bool
        Whether floating is enabled or not.
    align: str
        How to align contents.
    """
    def __init__(
            self,
            title: str = '',
            position:
                Literal['left-top', 'center-top', 'right-top',
                        'left-center', 'center', 'right-center',
                        'left-bottom', 'center-bottom', 'right-bottom'
                        ] = 'left-top',
            floating: bool = True,
            align: Literal['start', 'center', 'end'] = 'end',
            **kwargs
        ):
        self.title = title
        self.position = position
        self.floating = floating
        self.align = align
        super().__init__(**kwargs)



class ViewSourceMaterial(FloatingView):
    """List source materials.

    The number of materials is controlled by user input.

    Attributes
    ----------
    title: str
        The title of the table.
    position: str
        Initial position where the table is rendered.
    floating: bool
        Whether floating is enabled or not.
    align: str
        How to align contents.
    data: SourceMaterial
        Backend logic.
    """
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
            configuration=dict(clipboard=True), align=self.align
        )
        float_config = dict(
            headerControls=dict(
                close='remove', maximize='remove', minimize='remove'
            )
        )
        if self.floating:
            return pn.layout.FloatPanel(
                nrows, table,
                name='01. Source Material',
                margin=5,
                config=float_config
            )
        else:
            return pn.Column(
                nrows, table, name='01. Source Material', align=self.align
            )



class ViewPremixture(FloatingView):
    """Premixture design.

    The number of premixtures is controlled by user input.

    Attributes
    ----------
    title: str
        The title of the table.
    position: str
        Initial position where the table is rendered.
    floating: bool
        Whether floating is enabled or not.
    align: str
        How to align contents.
    data: PreMixture
        Backend logic.
    """
    data = param.ClassSelector(class_=PreMixture)

    def make_editor(self) -> dict:
        """Yield editor for Tabulator.
        
        Tabulator accepts editor that defines data type of each columns.
        """
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
        """Generate editable table.
        """
        parameterized = cast(PreMixture, self.data)
        parameter = cast(param.Parameter, parameterized.param.data)
        editor = self.make_editor()
        table = pn.widgets.Tabulator.from_param(
            parameter, editors=editor, show_index=False,
            configuration=dict(clipboard=True), align=self.align,
        )
        return table

    def __panel__(self):
        parameterized = cast(PreMixture, self.data)
        name = parameterized._name
        nrows = pn.widgets.IntInput.from_param(
            parameterized.param.nrows, start=1, step=1,
            name=f'N {name}', align=self.align
        )
        float_config = dict(
            headerControls=dict(
                close='remove', maximize='remove', minimize='remove'
            )
        )
        if self.floating:
            return pn.layout.FloatPanel(
                nrows, self.make_table,
                name=self.title, margin=20, config=float_config,
                position=self.position, contained=True,
            )
        else: 
            return pn.Column(
                nrows, self.make_table, name=self.title, align=self.align
            )



class ViewComposition(ViewPremixture):
    """Composition design.

    The number of compositions is controlled by user input.

    Attributes
    ----------
    title: str
        The title of the table.
    position: str
        Initial position where the table is rendered.
    floating: bool
        Whether floating is enabled or not.
    align: str
        How to align contents.
    data: Composition
        Backend logic.
    """
    data = param.ClassSelector(class_=Composition)

    def make_editor(self) -> dict:
        """Yield editor for Tabulator.
        
        Tabulator accepts editor that defines data type of each columns.
        """
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
    """Calcurated weight of eache materials for compositions.

    Attributes
    ----------
    title: str
        The title of the table.
    position: str
        Initial position where the table is rendered.
    floating: bool
        Whether floating is enabled or not.
    align: str
        How to align contents.
    data: Weight
        Backend logic.
    """
    data = param.ClassSelector(class_=Weight)

    @param.depends('data.digit', watch=False)
    def make_table(self) -> pn.widgets.Tabulator:
        """Generate editable table.
        """
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
        if self.floating:
            return pn.layout.FloatPanel(
                digit, self.make_table,
                name=self.title, margin=20, config=float_config,
                position=self.position, contained=True,
            )
        else:
            return pn.Column(digit, self.make_table, name=self.title)



class ViewWeightPreMixture(ViewWeight):
    """Calcurated weight of eache materials for premixtures.

    Attributes
    ----------
    title: str
        The title of the table.
    position: str
        Initial position where the table is rendered.
    floating: bool
        Whether floating is enabled or not.
    align: str
        How to align contents.
    data: WeightPremixture
        Backend logic.
    """
    data = param.ClassSelector(class_=WeightPremixture)

    @param.depends('data.digit', watch=False)
    def make_table(self) -> pn.widgets.Tabulator: # type: ignore[override]
        """Generate editable table.
        """
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
    """Record how weight materials for compositions.

    Attributes
    ----------
    title: str
        The title of the table.
    position: str
        Initial position where the table is rendered.
    floating: bool
        Whether floating is enabled or not.
    align: str
        How to align contents.
    data: Work
        Backend logic.
    threshold: float
        Acceptable error (%) for weighting.
    """
    data = param.ClassSelector(class_=Work)
    threshold = param.Number(default=0.01)

    def validate(self, value, target):
        """Check the weighted value is acceptable or not.
        
        Parameters
        ----------
        value: float
            Weighted amount.
        target: float
            Designed amount.
        
        Return
        ------
        res: str
            Acceptable -> "blue"
            Fail -> "red"
            Empty cell -> "black"
        """
        try:
            res = abs(value/target - 1) < self.threshold
            res = 'blue' if res else 'red'
        except ZeroDivisionError:
            res = 'blue' if np.isnan(value) else 'red'
        except TypeError:
            res = 'black'
        return res

    def coloring(self, s):
        """Yield color setting for each cells.
        
        Colors are decided baising on acceptable error or not.
        """
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
        """Generate editable table.
        """
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
        if self.floating:
            return pn.layout.FloatPanel(
                threshold, self.make_table,
                name=self.title, margin=20, config=float_config,
                position=self.position, contained=True,
            )
        else:
            return pn.Column(threshold, self.make_table, name=self.title)



class ViewWorkPreMixture(ViewWork):
    """Record how weight materials for premixtures.

    Attributes
    ----------
    title: str
        The title of the table.
    position: str
        Initial position where the table is rendered.
    floating: bool
        Whether floating is enabled or not.
    align: str
        How to align contents.
    data: WorkPreMixture
        Backend logic.
    threshold: float
        Acceptable error (%) for weighting.
    """
    data = param.ClassSelector(class_=WorkPreMixture)
    threshold = param.Number(default=0.01)

    @param.depends('data.data', 'threshold', watch=False)
    def make_table(self) -> pn.widgets.Tabulator: # type: ignore[override]
        """Generate editale table.
        """
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
    """Show resulted concentration of compositions.

    Attributes
    ----------
    title: str
        The title of the table.
    position: str
        Initial position where the table is rendered.
    floating: bool
        Whether floating is enabled or not.
    align: str
        How to align contents.
    data: Result
        Backend logic.
    """
    data = param.ClassSelector(class_=Result)

    @param.depends('data.data', watch=False)
    def make_table(self):
        """Generate static table.
        """
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
        if self.floating:
            return pn.layout.FloatPanel(
                self.make_table,
                name=self.title, margin=20, config=float_config,
                position=self.position, contained=True,
            )
        else:
            return pn.Column(self.make_table, name=self.title)



class ViewResultPreMixture(ViewResult):
    """Show resulted concentration of premixtures.

    Attributes
    ----------
    title: str
        The title of the table.
    position: str
        Initial position where the table is rendered.
    floating: bool
        Whether floating is enabled or not.
    align: str
        How to align contents.
    data: ResultPreMixture
        Backend logic.
    """
    data = param.ClassSelector(class_=ResultPreMixture)



class ProcessTable(pn.viewable.Viewer):
    """Recording table in the flow chart.
    
    Attributes
    ----------
    weight: Weight
    """
    weight = param.ClassSelector(class_=Weight, allow_refs=True)
    work = param.ClassSelector(class_=Work, allow_refs=True)
    result = param.ClassSelector(class_=Result, allow_refs=True)