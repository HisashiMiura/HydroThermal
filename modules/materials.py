from dataclasses import dataclass
from modules import thermo_dynamics
from modules.material_props import (
    FormulaIsotherm,
    PowerExpIsotherm,
    ConstantVaporConductivity,
    PowerExpVaporConductivity,
    NoLiquidDiffusivity,
    PiecewiseExpPolyDiffusivity,
)


@dataclass
class Material:

    # 名前
    name: str

    # 熱伝導率, W/(m K)
    lambda_h: float

    # 比熱, J/(kg K)
    c: float

    # 密度 kg/m3
    rho: float

    # 平衡含水率の部品
    isotherm: FormulaIsotherm | PowerExpIsotherm

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
    """材料の一覧。名前で材料を探す。

    材料の一覧は、呼ぶ側がローダー（material_loaders.py）で読み込んで渡す。
    例: Materials(load_whamcavity())
    """

    def __init__(self, ms: list[Material]):

        self.ms: list[Material] = ms

    def get_material(self, name: str) -> Material:
        
        ms = []

        for m in self.ms:

            if m.name == name:

                ms.append(m)
        
        if len(ms) == 0:
            raise KeyError('指定の名前の材料が見つかりませんでした。')
        
        elif len(ms) > 1:
            raise ValueError(f'同じ名前の材料が複数あります: {name}')
        
        else:

            return ms[0]
        
    def get_material_name(self) -> list[str]:
        """登録されている材料名称のリストを取得する。"""

        return [m.name for m in self.ms]
