import pandas as pd
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

    # 平衡含水率の部品
    isotherm: FormulaIsotherm

    # 湿気伝導率の部品
    vapor_conductivity: ConstantVaporConductivity | PowerExpVaporConductivity

    # 液水拡散係数の部品
    liquid_diffusivity: NoLiquidDiffusivity | PiecewiseExpPolyDiffusivity

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

        # material_loaders は Material を使うため、ファイルの先頭で読み込むと
        # 「materials → material_loaders → materials」と互いに読み込み合ってエラーになる。
        # そのため、ここで（呼ばれたときに）読み込む。
        from modules.material_loaders import _material_from_whamcavity_row

        # 1行ずつ取り出してデータクラスに格納
        ms = [_material_from_whamcavity_row(name=name, row=row) for name, row in df.iterrows()]

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
    
