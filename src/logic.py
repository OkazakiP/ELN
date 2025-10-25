# %%
from typing import Optional, Literal, cast
import numpy as np
import pandas as pd
import param



class SourceMaterial(param.Parameterized):
    """Manage Source Materials.
    
    Attributes
    -----------
    data: pd.DataFrame
        The table data.
    nrows: int
        Number of the table.
    columns: list of str
        Column names.
    names: list
        Material names.
    unit: str
        Calcuration unit. "wt%" or "mM".
    weight_percent: pd.DataFrame
        `data` in wt%.
    """
    data = param.DataFrame(allow_None=True, allow_refs=True)
    nrows = param.Integer(default=3, step=1, bounds=(1, None))
    names = param.List(allow_None=True)
    unit = param.String()

    def __init__(
            self,
            data: Optional[pd.DataFrame] = None,
            nrows: Optional[int] = None,
            columns: Optional[list[str]] = None,
            unit: Literal['wt%', 'mM'] = 'wt%',
            **params
        ):
        self.columns = self.make_column(columns, unit)
        if nrows is None:
            nrows = 3 if data is None else data.shape[0]
        super().__init__(data=data, nrows=nrows, names=None, unit=unit, **params)

    def make_row(self, i) -> list:
        row = (
            [f'Material {chr(ord("A")+i)}']
            + [None]*(len(self.columns)-2)
            + [100]
        )
        return row

    def make_column(self, columns, unit) -> list:
        if columns is None:
            columns = ['Material', 'Lot', 'wt%']
        if unit is not None:
            assert unit in ['wt%', 'mM'], f'`unit`={unit} must be "wt%" or "mM".'
            if unit not in columns:
                columns += [unit]
        else:
            wt = 'wt%' in columns
            m = 'mM' in columns
            assert ((wt and not m) or (not wt and m)), f'`unit`={unit} must be "wt%" or "mM".'
            unit = 'wt%' if wt else 'mM'
        if (unit == 'M') and ('g/mol' not in columns):
            columns += ['g/mol']
        return columns

    @param.depends('nrows', watch=True, on_init=True)
    def resize_table(self):
        nrows = cast(int, self.nrows)
        data = cast(pd.DataFrame, self.data)
        if self.data is None:
            self.data = pd.DataFrame(
                [self.make_row(i) for i in range(nrows)],
                columns=self.columns,
            )
        else:
            data = [
                data.iloc[i].to_list() if i<self.data.shape[0]
                else self.make_row(i) for i in range(nrows)
            ]
            self.data = pd.DataFrame(data, columns=self.columns).reset_index(drop=True)
    
    @param.depends('data', watch=True, on_init=True)
    def update_names(self):
        data = cast(pd.DataFrame, self.data)
        names = data['Material']
        if self.names is None:
            self.names = names.to_list()
        elif len(names) != len(cast(list, self.names)):
            self.names = names.to_list()
        elif not (names == self.names).all():
            self.names = names.to_list()
        else:
            return

    @property
    def weight_percent(self):
        data = cast(pd.DataFrame, self.data).copy()
        match self.unit:
            case 'wt%':
                return data
            case 'mM':
                data['wt%'] = (
                    data['mM']#mmol/L
                    .mul(data['g/mol'], axis=0)#mg/L
                    .div(1000)#g/L
                ).pipe(
                    lambda s:
                        s.div(s.add(1000)).mul(100)
                )
                return data
            case _:
                raise ValueError(f"`unit` = {self.unit} is not supported.")



class PreMixture(param.Parameterized):
    """Manage Source Materials.
    
    Attributes
    -----------
    data: pd.DataFrame
        The table data.
    nrows: int
        Number of the table.
    material: SourceMaterial
        Source materials to be used.
    names: list
        Premixture names.
    weight_percent: pd.DataFrame
        `data` in wt%.
    total: str
        'TotalWeight'/g or 'TotalVolume'/mL
    """
    data = param.DataFrame(allow_None=True, allow_refs=True)
    material = param.ClassSelector(class_=SourceMaterial)
    nrows = param.Integer(default=1, step=1, bounds=(1, None))
    names = param.List(allow_None=True)

    def __init__(
            self,
            material: SourceMaterial,
            data: Optional[pd.DataFrame] = None,
            nrows: int = 1,
            **params
        ):
        self._name = 'Premixture'
        super().__init__(
            data=data, material=material, nrows=nrows, names=None,
            **params
        )

    def make_row(self, i) -> list:
        material = cast(SourceMaterial, self.material)
        data = cast(pd.DataFrame, material.data)
        row = (
            [f'{chr(ord("a")+i)}']
            + [0.]*data.shape[0]
            + [100]
        )
        return row

    @param.depends('nrows', watch=True, on_init=False)
    def resize_table(self):
        _data = cast(pd.DataFrame, self.data)
        data = [
            _data.iloc[i].to_list() if i<_data.shape[0]
            else self.make_row(i) for i in range(cast(int, self.nrows))
        ]
        self.data = pd.DataFrame(
            data, columns=_data.columns
        ).reset_index(drop=True)

    @param.depends('data', watch=True, on_init=True)
    def update_names(self):
        _data = cast(pd.DataFrame, self.data)
        try:
            names = _data[self._name]
        except TypeError:
            names = pd.Series()
        if self.names is None:
            self.names = names.to_list()
        elif len(names) != len(cast(list, self.names)):
            self.names = names.to_list()
        elif not (names == self.names).all():
            self.names = names.to_list()
        else:
            return

    @param.depends('material.names', watch=True, on_init=True)
    def update_column(self):
        material = cast(SourceMaterial, self.material)
        unit = cast(str, material.unit)
        material_data = cast(pd.DataFrame, material.data)
        material_names = cast(list, material.names)
        match unit:
            case 'wt%':
                total = 'TotalWeight'
            case 'mM':
                total = 'TotalVolume'
            case _:
                raise ValueError(f"`material.unit` = {unit} is not supported.")

        if self.data is None:
            data = [self.make_row(i) for i in range(cast(int, self.nrows))]
            columns = (
                [self._name]
                + material_data['Material'].to_list()
                + [total]
            )
            data = pd.DataFrame(data, columns=columns)
        else:
            data = (
                cast(pd.DataFrame, self.data)
                .copy()
                .reset_index(drop=True)
            )
        value_old = data.drop([self._name], axis=1)
        name = data[self._name]
        value_append = pd.DataFrame(
            {key: [0.]*data.shape[0]
                for key in material_names if key not in data.columns},
        )
        self.data = pd.concat(
            [name, value_old, value_append],
            axis=1
        ).reindex(
            [self._name]+material_names+[total],
            axis=1
        )
        self.total = total

    @property
    def weight_percent(self):
        material = cast(SourceMaterial, self.material)
        unit = cast(str, material.unit)
        material_names = cast(list, material.names)
        material_data =cast(pd.DataFrame, material.data)
        data = cast(pd.DataFrame, self.data)
        match unit:
            case 'wt%':
                return data.assign(
                    Solvent=lambda d: 100 - d[material_names].sum(axis=1),
                )
            case 'mM':
                return (
                    data
                    .set_index(self._name)
                    .mul(
                        material_data.set_index('Material')['g/mol'],
                        axis=1)#mg/(1000 mL)
                    .div(1000)#g/(1000 mL)
                    .pipe(lambda d: d.div(d.sum(axis=1).add(1000)))
                    .mul(100)#wt%
                ).assign(
                    Solvent=lambda d: 100 - d.sum(axis=1),
                    TotalWeight=(
                        lambda d:
                            data['TotalVolume']
                            + data[material_names].sum(axis=1)
                    )
                ).reset_index(
                )
            case _:
                raise ValueError(f'`material.unit` = {unit} is not supported.')



class Composition(PreMixture):
    """Manager Composition.
    
    Attributes
    -----------
    data: pd.DataFrame
        The table data.
    nrows: int
        Number of the table.
    material: SourceMaterial
        Source materials to be used.
    premixture: PreMixture
        Premixtures to be used.
    total: str
        'TotalWeight'/g or 'TotalVolume'/mL
    density_solvent: float
        Density/(g/cm3) of the solvent.
    names: list
        Composition names.
    weight_percent: pd.DataFrame
        `data` in wt%.
    """
    data = param.DataFrame(allow_None=True, allow_refs=True)
    material = param.ClassSelector(class_=SourceMaterial)
    premixture = param.ClassSelector(class_=PreMixture, allow_None=True)
    nrows = param.Integer(default=3, step=1, bounds=(1, None))
    names = param.List(allow_None=True)

    def __init__(
            self,
            material: SourceMaterial,
            premixture: Optional[PreMixture] = None,
            data: Optional[pd.DataFrame] = None,
            nrows: int = 3,
            density_solvent: float = 1.,
            **params
        ):
        if premixture is None:
            premixture = PreMixture(material)
            premixture.names = list()
        self.density_solvent = density_solvent
        self._name = 'Composition'
        super(PreMixture, self).__init__(
            data=data, material=material, premixture=premixture,
            nrows=nrows, **params
        )

    def make_row(self, i) -> list:
        material = cast(SourceMaterial, self.material)
        material_names = cast(list, material.names)
        premixture = cast(PreMixture, self.premixture)
        premixture_names = cast(list, premixture.names)
        row = (
            [f'{chr(ord("A")+i)}']
            + [0.]*len(material_names)
            + [False]*len(premixture_names)
            + [100]
        )
        return row

    @param.depends(
        'material.names', 'premixture.names',
        watch=True, on_init=True)
    def update_column(self): # type: ignore[override]
        material = cast(SourceMaterial, self.material)
        material_names = cast(list, material.names)
        unit = cast(str, material.unit)
        premixture = cast(PreMixture, self.premixture)
        premixture_names = cast(list, premixture.names)
        match unit:
            case 'wt%':
                total = 'TotalWeight'
            case 'mM':
                total = 'TotalVolume'
            case _:
                raise ValueError(f"`material.unit` = {unit} is not supported.")
        if self.data is None:
            data = [self.make_row(i) for i in range(cast(int, self.nrows))]
            columns = (
                [self._name]
                + material_names
                + premixture_names
                + [total]
            )
            data = pd.DataFrame(data, columns=columns)
        else:
            data = (
                cast(pd.DataFrame, self.data)
                .copy()
                .reset_index(drop=True)
            )
        value_old = data.drop([self._name, total], axis=1)
        name = data[self._name]
        weight = data[total]
        value_append = pd.DataFrame(
            {key: [0.]*data.shape[0]
                for key in material_names if key not in data.columns},
        )
        bool_append = pd.DataFrame(
            {key: [False]*data.shape[0]
                for key in premixture_names if key not in data.columns},
        )
        self.data = pd.concat(
            [name, value_old, value_append, bool_append, weight],
            axis=1
        ).reindex(
            [self._name]+material_names+premixture_names+[total],
            axis=1
        )
        self.total = total

    @property
    def weight_percent(self):
        material = cast(SourceMaterial, self.material)
        material_data = cast(pd.DataFrame, material.data)
        unit = cast(str, material.unit)
        premixture = cast(PreMixture, self.premixture)
        premixture_names = cast(list, premixture.names)
        data = cast(pd.DataFrame, self.data)
        match unit:
            case 'wt%':
                return data.drop(premixture_names, axis=1)
            case 'mM':
                return (
                    data
                    .drop(premixture_names, axis=1)
                    .set_index(self._name)
                    .mul(
                        material_data.set_index('Material')['g/mol'],
                        axis=1)#mg/(1000 mL)
                    .div(1000)#g/(1000 mL)
                    .pipe(lambda d: d.div(d.sum(axis=1).add(1000)))
                    .mul(100)#wt%
                ).assign(
                    TotalWeight=lambda d: d['TotalVolume'] + d.sum(axis=1)
                ).reset_index(
                )
            case _:
                raise ValueError(f"`material.unit` = {unit} is not supported.")



class Weight(param.Parameterized):
    """Manage how to weight each materials and premixtures.
    
    Attribute
    ----------
    data: pd.DataFrame
        The table data.
    composition: Composition
        Composition design.
    digit: int
        Weighting digit.
    """
    data = param.DataFrame(allow_None=True, allow_refs=True)
    composition = param.ClassSelector(class_=Composition)
    digit = param.Integer(default=2)

    def __init__(
            self,
            composition: Composition,
            data: Optional[pd.DataFrame] = None,
            digit: int = 2,
            **params
        ):
        super().__init__(
            composition=composition, data=data, digit=digit,
            **params
        )

    @param.depends(
        'composition.data',
        'composition.material.data',
        'composition.premixture.data',
        'digit',
        watch=True, on_init=True
    )
    def update_data(self):
        composition = cast(Composition, self.composition)
        composition_data = cast(pd.DataFrame, composition.data).copy()
        material = cast(SourceMaterial, composition.material)
        material_names = cast(list[str], material.names)
        premixture = cast(PreMixture, composition.premixture)
        premixture_names = cast(list[str], premixture.names)

        # How weight each materials in the composition.
        composition_percent = composition.weight_percent
        try:
            data = (
                composition_percent
                .pipe(lambda d: d[material_names].mul(d['TotalWeight'], axis=0))
                .div(100)
            )
        except KeyError:
            # This method can be called before calling self.composition.update_column()
            return
        # How much premixtures are required.
        if composition_data[premixture_names].to_numpy().any():
            premixture, _premixture = self.calc_premixture(data)
        else:
            premixture = 0.
            _premixture = None
        # How much materials are required.
        data = data.assign(
            Solvent=(
                lambda d:
                    composition_percent
                    ['TotalWeight']
                    .sub(d.sum(axis=1), axis=0)
            )
        ).sub(
            premixture
        )
        lack = data.copy()
        data = data.div(
            material.weight_percent.set_index('Material')['wt%'],
            axis=1
        ).mul(
            100
        )
        data['Solvent'] = lack.sum(axis=1) - data.sum(axis=1)
        data = data.round(cast(int, self.digit))
        self.data = pd.concat(
            [composition_data['Composition'], data, _premixture],
            axis=1
        ).reindex(
            ['Composition']+list(material_names)
                +list(premixture_names)+['Solvent'],
            axis=1
        )

    def calc_premixture(
            self,
            data: pd.DataFrame
        ) -> tuple[pd.DataFrame, pd.DataFrame]:
        composition = cast(Composition, self.composition)
        composition_data = cast(pd.DataFrame, composition.data)
        composition_names = cast(list[str], composition.names)
        premixture = cast(PreMixture, composition.premixture)
        premixture_percent = premixture.weight_percent
        premixture_names = cast(list[str], premixture.names)
        premixture_data = cast(pd.DataFrame, premixture.data)

        material = cast(SourceMaterial, composition.material)
        material_names = cast(list[str], material.names)
        # How much premixtures are required.
        factor = (
            data.to_numpy()
            / np.expand_dims(premixture_data[material_names].to_numpy(), 1)
        )
        factor[np.isnan(factor)|(factor==0.)] = 1.
        _shape = (len(premixture_names), len(composition_names), 1)
        factor = factor.min(axis=2).reshape(_shape)
        # Weight by Premixture
        premixture = (
            premixture_percent
            .drop(['Premixture', 'TotalWeight'], axis=1)
            .to_numpy()
            .reshape(len(premixture_names), 1, len(material_names)+1)
        )
        _premixture = (
            composition_data[premixture_names].to_numpy().T.reshape(_shape)
            * factor
            * premixture
        )
        premixture = _premixture.sum(axis=0)
        # How much premixtures are required.
        _premixture = (
            _premixture
            / premixture_percent
                .drop(['Premixture', 'TotalWeight'], axis=1)
                .to_numpy()
                .reshape(len(premixture_names), 1, len(material_names)+1)
            * 100
        )
        _premixture[np.isnan(_premixture)] = 0.
        _premixture = pd.DataFrame(
            _premixture.max(axis=2).T,
            columns=premixture_names
        )
        premixture = pd.DataFrame(
            premixture,
            columns=material_names+['Solvent']
        )
        return premixture, _premixture 



class WeightPremixture(Weight):
    """Manage how to weight materials for premixtures.
    
    Attribute
    ----------
    data: pd.DataFrame
        The table data.
    premixture: PreMixture
        Premixture design.
    digit: int
        Weighting accuracy.
    """
    data = param.DataFrame(allow_None=True, allow_refs=True)
    premixture = param.ClassSelector(class_=PreMixture)
    digit = param.Integer(default=2)

    def __init__(
            self,
            premixture: PreMixture,
            data: Optional[pd.DataFrame] = None,
            digit: int = 2,
            **params
        ):
        super(Weight, self).__init__(
            premixture=premixture, data=data, digit=digit,
            **params
        )

    @param.depends(
        'premixture.data',
        'premixture.material.data',
        'digit',
        watch=True, on_init=True
    )
    def update_data(self): # type: ignore[override]
        premixture = cast(PreMixture, self.premixture)
        premixture_data = cast(pd.DataFrame, premixture.data)
        material = cast(SourceMaterial, premixture.material)
        material_names = cast(list[str], material.names)

        # How weight each materials in the composition.
        data = (
            premixture.weight_percent
            .pipe(lambda d: d[material_names].mul(d['TotalWeight'], axis=0))
            .div(100)
        )
        # How much materials are required.
        data = data.assign(
            Solvent=(
                lambda d:
                    premixture.weight_percent
                    ['TotalWeight']
                    .sub(d.sum(axis=1), axis=0)
            )
        )
        lack = data.copy()
        data = data.div(
            material.weight_percent.set_index('Material')['wt%'],
            axis=1
        ).mul(
            100
        )
        data['Solvent'] = lack.sum(axis=1) - data.sum(axis=1)
        data = data.round(cast(int, self.digit))
        self.data = pd.concat(
            [premixture_data[premixture._name], data],
            axis=1
        ).reindex(
            [premixture._name]+list(material_names)+['Solvent'],
            axis=1
        )
    


class Work(param.Parameterized):
    """Loggin how weight each materials and premixtures for compositions.
    
    Attribute
    ----------
    data: pd.DataFrame
        The table data.
    weight: Weight
        Weighting design.
    """
    data = param.DataFrame(allow_None=True)
    weight = param.ClassSelector(class_=Weight)

    def __init__(
            self,
            weight: Weight,
            **params
        ):
        super().__init__(weight=weight, **params)

    @param.depends('weight.data', watch=True, on_init=True)
    def update_data(self):
        weight = cast(Weight, self.weight)
        data = cast(pd.DataFrame, weight.data).set_index('Composition').copy()
        data[slice(None)] = np.nan
        self.data = data.reset_index()



class WorkPreMixture(param.Parameterized):
    """Logging how weight each materials for premixtures.
    
    Attribute
    ----------
    data: pd.DataFrame
        The table data.
    weight: WeightPremixture
        Weighting design for premixtures.
    """
    data = param.DataFrame(allow_None=True)
    weight = param.ClassSelector(class_=WeightPremixture)

    def __init__(
            self,
            weight: Weight,
            **params
        ):
        super().__init__(weight=weight, **params)

    @param.depends('weight.data', watch=True, on_init=True)
    def update_data(self):
        weight = cast(WeightPremixture, self.weight)
        premixture = cast(PreMixture, weight.premixture)
        data = (
            cast(pd.DataFrame, weight.data)
            .set_index(premixture._name)
            .copy()
        )
        data[slice(None)] = np.nan
        self.data = data.reset_index()



class ResultPreMixture(param.Parameterized):
    """Calcucate resulting composition of premixtures.
    
    Attributes
    -----------
    data: pd.DataFrame
        The table data.
    work: WorkPreMixture
        Log of making premixture.
    """
    data = param.DataFrame(allow_None=True)
    work = param.ClassSelector(class_=WorkPreMixture)

    def __init__(
            self,
            work: WorkPreMixture,
            **kwargs
        ):
        super().__init__(work=work, **kwargs)

    @param.depends('work.data', watch=True, on_init=True)
    def calc(self):
        work = cast(WorkPreMixture, self.work)
        weight = cast(WeightPremixture, work.weight)
        premixture = cast(PreMixture, weight.premixture)
        material = cast(SourceMaterial, premixture.material)

        data = cast(pd.DataFrame, work.data).set_index(premixture._name)
        total = data.sum(axis=1)
        data = (
            data[material.names]
            .mul(
                material.weight_percent.set_index('Material')['wt%'],
                axis=1)
            .div(total, axis=0)
            .reset_index()
        )
        self.data = data



class Result(param.Parameterized):
    """Calcucate resulting compositions.
    
    Attributes
    -----------
    data: pd.DataFrame
        The table data.
    work: Work
        Log of making composition.
    result_premixture: ResultPreMixture
        Resulting compositions of premixtures.
    """
    data = param.DataFrame(allow_None=True)
    work = param.ClassSelector(class_=Work)
    result_premixture = param.ClassSelector(class_=ResultPreMixture)

    def __init__(
            self,
            work: Work,
            result_premixture: Optional[ResultPreMixture] = None,
            **params
        ):
        if result_premixture is None:
            weight = cast(Weight, work.weight)
            composition = cast(Composition, weight.composition)
            premixture = cast(PreMixture, composition.premixture)
            weight_premixture = WeightPremixture(premixture)
            work_premixture = WorkPreMixture(weight_premixture)
            result_premixture = ResultPreMixture(work_premixture)
        super().__init__(
            work=work, result_premixture=result_premixture, **params
        )

    @param.depends('work.data', watch=True, on_init=True)
    def calc(self):
        work = cast(Work, self.work)
        weight = cast(Weight, work.weight)
        composition = cast(Composition, weight.composition)
        composition_names = cast(list[str], composition.names)
        material = cast(SourceMaterial, composition.material)
        material_names = cast(list[str], material.names)
        premixture = cast(PreMixture, composition.premixture)
        premixture_names = cast(list[str], premixture.names)
        result_premixture = cast(ResultPreMixture, self.result_premixture)
        res_premixture_data = cast(pd.DataFrame, result_premixture.data)

        data = cast(pd.DataFrame, work.data).set_index(composition._name)
        total = data.sum(axis=1)
        data_premixture = (
            data[premixture_names]
            .to_numpy()
            .T
            .reshape(len(premixture_names), len(composition_names), 1)
        ) * (
            np.expand_dims(res_premixture_data[material_names].to_numpy(), 1)
        )
        data_premixture[np.isnan(data_premixture)] = 0.
        data_premixture = data_premixture.sum(axis=0)
        data_premixture = pd.DataFrame(
            data_premixture, columns=material_names,
            index=cast(list[str], composition.names)
        ).rename_axis(
            composition._name
        )
        data_material = (
            data[material.names]
            .mul(
                material.weight_percent.set_index('Material')['wt%'],
                axis=1)
        ).fillna(0.)
        data = data_premixture.add(data_material).div(total, axis=0).reset_index()
        self.data = data



# %%
if __name__=='__main__':
    material = SourceMaterial(
        data=pd.DataFrame(
            [['Material 1', None, 100],
             ['Material 2', None, 50],
             ['Material 3', None, 1],
            ],
            columns=['Material', 'Lot', 'wt%']
        )
    )
    premixture = PreMixture(
        data=pd.DataFrame(
            [['Premixture a', 20., 0., 0., 500],
             ['Premixture b', 20., 20., 0., 500]
             ],
            columns=['Premixture', 'Material 1', 'Material 2', 'Material 3', 'TotalWeight'],
        ),
        material=material
    )
    composition = Composition(
        data=pd.DataFrame(
            [['Composition 1', 10., 10, 0.1, False, True, 100],
             ['Composition 2', 10, 10., 0., True, False, 200],
             ['Composition 3', 10, 0., 0.1, True, False, 200],
             ],
            columns=['Composition', 'Material 1', 'Material 2', 'Material 3', 'Premixture a', 'Premixture b', 'TotalWeight']
        ),
        material=material,
        premixture=premixture
    )
    weight = Weight(composition=composition)
    work = Work(weight)
    weight_premixture = WeightPremixture(premixture=premixture,)
    material_data = cast(pd.DataFrame, material.data)
    material.data = pd.concat(
        [material_data, pd.DataFrame([['Material 4', None, 100]], columns=material_data.columns)],
        axis=0
    ).reset_index(drop=True)
    result = Result(work)