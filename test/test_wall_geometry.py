import dataclasses

import pytest

from modules.material_loaders import load_materials
from modules.materials import Materials
from modules.thermo_dynamics import ROW_CP
from modules import wall_geometry
from modules.wall_geometry import MaterialNode, AirNode, _make_nodes, material_finder
from modules.wall_input import MaterialLayerInput, AirLayerInput


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
        # 厚さ 25 mm、α = 0.085
        node = AirNode(thickness=0.025, alpha=0.085, layer_index=1)
        assert (node.width, node.alpha) == (0.025, 0.085)
        assert node.heat_capacity == pytest.approx(0.025 * ROW_CP)

    def test_r_h(self):
        # よく混ざった空気なので、端までの熱抵抗は 0
        node = AirNode(thickness=0.025, alpha=0.085, layer_index=1)
        assert (node.r_h_left, node.r_h_right) == (0.0, 0.0)

    @pytest.mark.parametrize('thickness, alpha, key', [(0.0, 0.085, 'thickness'), (0.025, -0.1, 'alpha')])
    def test_invalid_value(self, thickness, alpha, key):
        with pytest.raises(ValueError, match=key):
            AirNode(thickness=thickness, alpha=alpha, layer_index=1)


def _layer(name: str, thickness: float, n_div: int) -> MaterialLayerInput:
    """旧 Excel の材料の層の入力（初期の温湿度は 10 deg.C・50%）。"""
    return MaterialLayerInput(source='whamcavity', name=name, thickness=thickness, n_div=n_div,
                              initial_temperature=10.0, initial_rh=50.0)


def _air_layer() -> AirLayerInput:
    """通気層 25 mm、α = 0.085。"""
    return AirLayerInput(thickness=0.025, alpha=0.085, initial_temperature=15.0, initial_rh=50.0)


def _main_wall_layers() -> tuple:
    """今の main.py・Fortran の入力の壁 7 層。"""
    return (
        _layer('サイディング', 0.016, 5), _air_layer(), _layer('石膏ボード', 0.042, 5), _layer('構造用合板1', 0.009, 6),
        _layer('グラスウール1', 0.1, 5), _layer('構造用合板1', 0.012, 6), _layer('石膏ボード', 0.042, 5),
    )


class TestMakeNodes:

    def test_one_layer(self):
        # 合板 9 mm・分割数 6：質点 6 個、両端は表面の側までの距離が 0
        nodes = _make_nodes((_layer('構造用合板1', 0.009, 6),), find_material=material_finder())
        assert len(nodes) == 6
        assert nodes[0].d_left == 0.0
        assert nodes[-1].d_right == 0.0
        assert sum(n.width for n in nodes) == pytest.approx(0.009)

    def test_interior_width(self):
        # 層の中の質点の幅は dx = 9 mm / 5 = 1.8 mm、両端は dx / 2
        nodes = _make_nodes((_layer('構造用合板1', 0.009, 6),), find_material=material_finder())
        assert [n.width for n in nodes] == pytest.approx([0.0009, 0.0018, 0.0018, 0.0018, 0.0018, 0.0009])

    def test_two_layers_boundary(self):
        # 合板とグラスウールの境目に、同じ位置の質点が 2 つ並ぶ（どちらも境目の側までの距離が 0）
        layers = (_layer('構造用合板1', 0.009, 6), _layer('グラスウール1', 0.1, 5))
        nodes = _make_nodes(layers, find_material=material_finder())
        left, right = nodes[5], nodes[6]
        assert (left.d_right, right.d_left) == (0.0, 0.0)
        assert (left.layer_index, right.layer_index) == (0, 1)
        assert (left.material.name, right.material.name) == ('構造用合板1', 'グラスウール1')

    def test_air_layer(self):
        # 通気層は空気の質点 1 つで、流量係数は入力の α のまま
        layers = (_layer('サイディング', 0.016, 5), _air_layer(), _layer('石膏ボード', 0.042, 5))
        nodes = _make_nodes(layers, find_material=material_finder())
        air = nodes[5]
        assert isinstance(air, AirNode)
        assert (air.thickness, air.alpha) == (0.025, 0.085)
        assert air.layer_index == 1

    def test_main_wall(self):
        # 今の壁 7 層：質点 33 個（今の Wall.read と同じ 5 + 1 + 5 + 6 + 5 + 6 + 5）
        nodes = _make_nodes(_main_wall_layers(), find_material=material_finder())
        assert len(nodes) == 33

    def test_width_of_each_layer(self):
        # 各層の質点の幅の合計が、その層の厚さ
        layers = _main_wall_layers()
        nodes = _make_nodes(layers, find_material=material_finder())
        for i, layer in enumerate(layers):
            assert sum(n.width for n in nodes if n.layer_index == i) == pytest.approx(layer.thickness)

    def test_material_not_found(self):
        layers = (_layer('構造用合板1', 0.009, 6), _layer('構造用合板3', 0.009, 6))
        with pytest.raises(ValueError, match="層 1 番目.*構造用合板3"):
            _make_nodes(layers, find_material=material_finder())


class TestMaterialFinder:

    def test_load_once(self, monkeypatch):
        # 同じ出どころを何回探しても、Excel を読み込むのは 1 回だけ
        calls = []

        def counting_load_materials(source):
            calls.append(source)
            return load_materials(source)

        monkeypatch.setattr(wall_geometry, 'load_materials', counting_load_materials)
        find = material_finder()
        find('whamcavity', '構造用合板1')
        find('whamcavity', 'グラスウール1')
        assert calls == ['whamcavity']
