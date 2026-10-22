import dataclasses

import pytest

from modules.material_loaders import load_materials
from modules.materials import Materials
from modules.thermo_dynamics import ROW_CP
from modules.wall_geometry import MaterialNode, AirNode


def _plywood():
    """構造用合板1（旧 Excel）。"""
    return Materials(load_materials('whamcavity')).get_material(name='構造用合板1')


class TestMaterialNode:

    @pytest.mark.parametrize('d_left, d_right, width', [
        (0.001, 0.001, 0.002),   # 層の中
        (0.0, 0.001, 0.001),     # 層の左の端
        (0.001, 0.0, 0.001),     # 層の右の端
    ])
    def test_width(self, d_left, d_right, width):
        node = MaterialNode(d_left=d_left, d_right=d_right, material=_plywood(), layer_index=0)
        assert node.width == pytest.approx(width)

    def test_heat_capacity(self):
        # 幅 2 mm × 容積比熱
        m = _plywood()
        node = MaterialNode(d_left=0.001, d_right=0.001, material=m, layer_index=0)
        assert node.heat_capacity == pytest.approx(0.002 * m.c * m.rho)

    @pytest.mark.parametrize('d_left, d_right', [
        (0.001, 0.001),   # 層の中
        (0.0, 0.001),     # 層の左の端（左は 0）
        (0.001, 0.0),     # 層の右の端（右は 0）
    ])
    def test_r_h(self, d_left, d_right):
        # 端までの熱抵抗 = 距離 / 熱伝導率
        m = _plywood()
        node = MaterialNode(d_left=d_left, d_right=d_right, material=m, layer_index=0)
        assert node.r_h_left == pytest.approx(d_left / m.lambda_h)
        assert node.r_h_right == pytest.approx(d_right / m.lambda_h)

    def test_frozen(self):
        node = MaterialNode(d_left=0.001, d_right=0.001, material=_plywood(), layer_index=0)
        with pytest.raises(dataclasses.FrozenInstanceError):
            node.d_left = 0.0

    @pytest.mark.parametrize('d_left, d_right', [(-0.001, 0.001), (0.001, -0.001), (0.0, 0.0)])
    def test_invalid_distance(self, d_left, d_right):
        with pytest.raises(ValueError, match='d_left'):
            MaterialNode(d_left=d_left, d_right=d_right, material=_plywood(), layer_index=0)


class TestAirNode:

    def test_values(self):
        # 厚さ 25 mm、α = 0.085、横の長さ 0.42 m
        node = AirNode(thickness=0.025, alpha_a=0.085 * 0.025 * 0.42, layer_index=1)
        assert node.width == 0.025
        assert node.heat_capacity == pytest.approx(0.025 * ROW_CP)

    def test_r_h(self):
        # よく混ざった空気なので、端までの熱抵抗は 0
        node = AirNode(thickness=0.025, alpha_a=0.001, layer_index=1)
        assert (node.r_h_left, node.r_h_right) == (0.0, 0.0)

    @pytest.mark.parametrize('thickness, alpha_a, key', [(0.0, 0.001, 'thickness'), (0.025, -0.001, 'alpha_a')])
    def test_invalid_value(self, thickness, alpha_a, key):
        with pytest.raises(ValueError, match=key):
            AirNode(thickness=thickness, alpha_a=alpha_a, layer_index=1)
