import pandas as pd
from pandas import Series
import os
from dataclasses import dataclass
import logging
from modules import thermo_dynamics
from modules.material_props import (
    FormulaIsotherm,
    ConstantVaporConductivity,
    PowerExpVaporConductivity,
    NoLiquidDiffusivity,
    PiecewiseExpPolyDiffusivity,
)


logger = logging.getLogger(__name__)


@dataclass
class Material:

    # 名前
    name: str

    # 熱伝導率, W/(m K)
    lambda_h: float

    # 湿気伝導率, (kg/s)/(m Pa)
    lambda_dsh_m: float

    # 比熱, J/(kg K)
    c: float

    # 密度 kg/m3
    rho: float

    # 空隙率, m3/m3
    psi0: float

    # 平衡含水率の部品
    isotherm: FormulaIsotherm

    # 湿気伝導率の部品
    vapor_conductivity: ConstantVaporConductivity | PowerExpVaporConductivity

    # 液水拡散係数の部品
    liquid_diffusivity: NoLiquidDiffusivity | PiecewiseExpPolyDiffusivity

    @classmethod
    def load(cls, name: str, row: Series):

        # 熱伝導率, W/(m K)
        thermal_conductivity = row['thermal_conductivity(W/mK)']
        # 湿気伝導率, (kg/s)/(m Pa)
        moisture_conductivity = row['moisture_conductivity(kg/msPa)']
        # 比熱, J/(kg K)
        specific_heat = row['specific_heat(J/kgK)']
        # 密度, kg/m3
        density = row['density(kg/m3)']
        # エクセルの方もあわせて、列ヘッダ名を porosity(m3/m3) に直すこと。
        porosity = row['porosity']

        n_formula_branches = row['n_formula_branches']
        formula1 = str(row['formula1'])
        formula2 = str(row['formula2'])
        formula3 = str(row['formula3'])
        threshold2 = row['threshold2']
        threshold3 = row['threshold3']

        # 平衡含水率の部品
        # 旧 Excel では境目3 が境目2 より大きい前提なので、境目3 → 境目2 の順に調べるように並べる。
        if n_formula_branches == 1:
            candidates = []
        elif n_formula_branches == 2:
            candidates = [(threshold2, formula2)]
        elif n_formula_branches == 3:
            candidates = [(threshold3, formula3), (threshold2, formula2)]
        else:
            raise ValueError(f'{name}: n_formula_branches が不正です: {n_formula_branches}')

        # 境目が空欄の組は選ばれることがないので除く
        conditional = tuple((float(t), f) for t, f in candidates if not pd.isna(t))

        isotherm = FormulaIsotherm(formula=formula1, conditional=conditional)

        # 湿気伝導率の部品
        # 構造用合板1 は、湿度によって変わる式（ASHRAE）を使う。
        # 旧 Excel に係数の列がないため、Fortran（Whamcavity.f95）に直書きされている係数を使う。
        # （Fortran の元のコードには「*3.45」がコメントアウトされて残っている。理由は不明。）
        if name == '構造用合板1':
            vapor_conductivity = PowerExpVaporConductivity(a=1.87E-11, b=2.4019, c=-0.78864, d=1.1471)
        else:
            vapor_conductivity = ConstantVaporConductivity(value=moisture_conductivity)

        # 液水拡散係数の部品
        # 構造用合板1 だけ液水が移動する。旧 Excel に係数の列がないため、
        # Fortran（Whamcavity.f95 の DIFF）に直書きされている係数と範囲（含水率 45% を超え 110% 未満）を使う。
        # 部品の範囲は「下限を超え、上限以下」なので、含水率がちょうど 1.10 のときだけ Fortran と異なる。
        # （Fortran では RH 90% を超えるときだけ DIFF を呼んでいたが、構造用合板1 の含水率が 0.45 を超えるのは
        #   RH 約 98% より上なので、範囲の判定だけで同じ結果になる。）
        if name == '構造用合板1':
            liquid_diffusivity = PiecewiseExpPolyDiffusivity(ranges=(
                (0.45, 1.10, (-30.91, 4.2967, -0.22017, 0, 0, 0, 0)),
            ))
        else:
            liquid_diffusivity = NoLiquidDiffusivity()

        return Material(
            name=name,
            lambda_h=thermal_conductivity,
            lambda_dsh_m=moisture_conductivity,
            c=specific_heat,
            rho=density,
            psi0=porosity,
            isotherm=isotherm,
            vapor_conductivity=vapor_conductivity,
            liquid_diffusivity=liquid_diffusivity
        )

    def get_u(self, rh: float) -> float:
        """含水率（0.0～1.0）を求める。（質量含水率） ユー JIS A 1476 で建築材料の含水率測定法 が決められている。
           ちなみに、容積含水率の場合はプサイを使う場合が多いらしい。

        Args:
            rh: 相対湿度(0.0～100.0), %

        Returns:
            質量含水率（0.0～1.0）, kg/kg 水分の重量÷材料の乾燥重量
        """

        r = rh * 0.01

        return self.isotherm.u(r)

    def get_lambda_dsh_m(self, rh: float) -> float:
        """湿気伝導率を求める。
        
        Args:
            rh: 相対湿度(0.0～100.0), %
        
        Returns:
            湿気伝導率, (kg/s)/(m Pa)
        """

        return self.vapor_conductivity.lambda_dsh_m(rh * 0.01)

    def get_lambda_dsh_mu_l(self, rh: float, t: float) -> float:
        """水分化学ポテンシャル勾配に対する液相水分伝導率, (kg/s)/(m (J/kg)) を求める。
        Args:
            rh: 相対湿度(0.0～100.0), %
            t: 絶対温度, K
        Returns:
            液相水分伝導率, (kg/s)/(m (J/kg))
        """

        return thermo_dynamics.get_lambda_dsh_mu_l(rh=rh, t=t, get_u=self.get_u, d_w=self.liquid_diffusivity.d_w)

    def get_dpsi_dmu(self, mu: float, t: float):
        """水分化学ポテンシャル変化に対する含水率変化 (DPDU) を計算する。
            (m3/m3)/(J/kg)
            分子：含水率, m3/m3
            分母：水分化学ポテンシャル, J/kg
        
        Args:
            mu: 水分化学ポテンシャル, J/kg
            t: 絶対温度, K
        Returns:
            水分化学ポテンシャル変化に対する含水率変化, (m3/m3)/(J/kg)
        """

        return thermo_dynamics.get_dpsi_dmu(mu=mu, t=t, gma=self.rho, get_u=self.get_u)

    @property
    def c_rho(self):
        """容積比熱, J/(m3 K)"""
        return self.c * self.rho


class Materials:

    def __init__(self):

        self.ms: list[Material] = self.load()
    
    @classmethod
    def load(cls):

        file_name = 'materials_whamcavity.xlsx'

        # 絶対 path の取得
        current_dir = os.path.dirname(os.path.abspath(__file__))
        path_and_filename = os.path.join(current_dir, file_name)

        if not os.path.isfile(path_and_filename):
            raise FileNotFoundError(f'材料物性ファイルが見つかりません: {path_and_filename}')

        df = pd.read_excel(path_and_filename, sheet_name='material_prop', index_col='name')

        # インデックス（name）に重複がないかチェック
        if not df.index.is_unique:
            # 重複している名前を特定してエラーメッセージに入れる
            duplicates = df.index[df.index.duplicated()].unique().tolist()
            raise ValueError(f"{file_name} の 'name' 列に重複があります: {duplicates}")

        # 1行ずつ取り出してデータクラスに格納
        ms = [Material.load(name=name, row=row) for name, row in df.iterrows()]

        logger.info('材料物性データの読み込みに成功しました: %s（%d件）', file_name, len(ms))

        return ms
    


    def get_material(self, name: str) -> Material:
        
        ms = []

        for m in self.ms:

            if m.name == name:

                ms.append(m)
        
        if len(ms) == 0:
            raise KeyError('指定の名前の材料が見つかりませんでした。')
        
        elif len(ms) > 2:
            raise Exception()
        
        else:

            return ms[0]
        
    def get_material_name(self) -> list[str]:
        """登録されている材料名称のリストを取得する。"""

        return [m.name for m in self.ms]
    
