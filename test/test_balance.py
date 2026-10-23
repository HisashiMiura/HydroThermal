import numpy as np
import pytest

from modules.balance import heat_flow_ks
from modules.thermo_dynamics import ATP
from modules.wall_geometry import WallGeometry
from modules.wall_input import WallInput


def _one_layer_geometry() -> WallGeometry:
    """1 層の壁：構造用合板1 9 mm（分割数 6）、外表面 22.4、内表面 9.2。"""
    return WallGeometry.from_input(WallInput.from_dict({
        'surface': {'direction': 'e', 'angle': 90.0, 'albedo': 0.3, 'absorptance': 0.9, 'emissivity': 0.9, 'eva_height': 4.2},
        'layers': [{'source': 'whamcavity', 'name': '構造用合板1', 'thickness': 0.009, 'n_div': 6,
                    'initial_temperature': 10.0, 'initial_rh': 50.0}],
        'interfaces': [{'cond_h': 22.4, 'cond_m': 2.0e-11}, {'cond_h': 9.2, 'cond_m': 2.6e-10}],
        'len_vertical': 1.0,
        'len_horizontal': 1.0,
        'height': 1.0,
    }))


class TestHeatFlow:

    def test_uniform(self):
        # 外気・室内・全部の質点が 20 deg.C なら、熱は流れない
        g = _one_layer_geometry()
        t = 20.0 + ATP
        q_ks = heat_flow_ks(g, np.full(len(g.nodes), t), t_outdoor=t, t_indoor=t)
        np.testing.assert_allclose(q_ks, 0.0)

    def test_steady(self):
        # 外気 0 deg.C・室内 20 deg.C の定常の温度分布（抵抗に比例した直線）を入れると、
        # どのつながりの熱の流れも同じで、(0 - 20) / 熱貫流抵抗 に等しい
        g = _one_layer_geometry()
        r_h_ks = np.array([link.r_h for link in g.links])
        t_outdoor, t_indoor = 0.0 + ATP, 20.0 + ATP
        q = (t_outdoor - t_indoor) / r_h_ks.sum()

        # 質点 i の温度 = 外気温 - q × (つながり 0〜i の熱抵抗の和)
        t_is = t_outdoor - q * np.cumsum(r_h_ks)[:-1]

        q_ks = heat_flow_ks(g, t_is, t_outdoor=t_outdoor, t_indoor=t_indoor)
        np.testing.assert_allclose(q_ks, q)

    def test_direction(self):
        # 外気のほうが温かければ、外気側から室内側へ（正の向きに）流れる
        g = _one_layer_geometry()
        t = 20.0 + ATP
        q_ks = heat_flow_ks(g, np.full(len(g.nodes), t), t_outdoor=t + 10.0, t_indoor=t)
        assert q_ks[0] > 0.0
        assert q_ks[-1] == pytest.approx(0.0)

    def test_number(self):
        # 流れの数は、つながりの数（質点の数 + 1）
        g = _one_layer_geometry()
        q_ks = heat_flow_ks(g, np.full(len(g.nodes), 293.15), t_outdoor=293.15, t_indoor=293.15)
        assert len(q_ks) == len(g.links) == len(g.nodes) + 1
