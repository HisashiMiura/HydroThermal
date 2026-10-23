import dataclasses

import pytest

from modules.direction import Direction
from modules.material_loaders import load_materials
from modules.materials import Materials
from modules.state import State
from modules.thermo_dynamics import ROW_CP, ATP
from modules import wall_geometry
from modules.wall_geometry import MaterialNode, AirNode, _make_nodes, _make_links, material_finder, Link, Interface, Surface, Outdoor, Indoor, OUTDOOR, INDOOR
from modules.wall_input import MaterialLayerInput, AirLayerInput, InterfaceInput


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


def _node(name: str, d_left: float, d_right: float, layer_index: int) -> MaterialNode:
    """旧 Excel の材料の質点。"""
    return MaterialNode(d_left=d_left, d_right=d_right, material=material_finder()('whamcavity', name), layer_index=layer_index)


def _interface(cond_h: float) -> Interface:
    """熱コンダクタンス cond_h の境目（湿気は 7.75e-7）。計算の側の境目なので抵抗で持つ。"""
    return Interface(r_h=1.0 / cond_h, r_m=1.0 / 7.75e-7)


def _interface_input(cond_h: float) -> InterfaceInput:
    """熱コンダクタンス cond_h の入力の境目（湿気は 7.75e-7）。_make_links に渡す。"""
    return InterfaceInput(cond_h=cond_h, cond_m=7.75e-7)


class TestLinkHeat:

    def test_interior(self):
        # 合板の中の 2 つの質点（左右とも 0.9 mm）：熱抵抗 = 1.8 mm / λ
        a, b = _node('構造用合板1', 0.0009, 0.0009, 0), _node('構造用合板1', 0.0009, 0.0009, 0)
        link = Link(left=a, right=b, interface=None)
        assert link.r_h == pytest.approx(0.0018 / a.material.lambda_h)

    def test_layer_to_layer(self):
        # 合板の右の端と GW の左の端：境目の 1/50 だけ（1 回だけ入る）
        a, b = _node('構造用合板1', 0.0009, 0.0, 0), _node('グラスウール1', 0.0, 0.0125, 1)
        link = Link(left=a, right=b, interface=_interface(50.0))
        assert link.r_h == pytest.approx(1 / 50.0)

    def test_outside_surface(self):
        # 外気とサイディングの左の端：外表面の伝達 1/22.4 だけ
        link = Link(left=OUTDOOR, right=_node('サイディング', 0.0, 0.002, 0), interface=_interface(22.4))
        assert link.r_h == pytest.approx(1 / 22.4)

    def test_inside_surface(self):
        # 石膏ボードの右の端と室内：内表面の伝達 1/9.2 だけ
        link = Link(left=_node('石膏ボード', 0.00525, 0.0, 6), right=INDOOR, interface=_interface(9.2))
        assert link.r_h == pytest.approx(1 / 9.2)

    def test_air_layer(self):
        # サイディングの右の端と空気の質点：通気層の中の伝達 1/9.2 だけ
        air = AirNode(thickness=0.025, alpha=0.085, layer_index=1)
        link = Link(left=_node('サイディング', 0.002, 0.0, 0), right=air, interface=_interface(9.2))
        assert link.r_h == pytest.approx(1 / 9.2)

    def test_outdoor_indoor_resistance(self):
        # 外気・室内は質点ではないので、端までの抵抗は 0
        assert (OUTDOOR.r_h_right, INDOOR.r_h_left) == (0.0, 0.0)
        assert OUTDOOR == Outdoor() and INDOOR == Indoor()

    def test_indoor_on_left(self):
        with pytest.raises(ValueError, match='left'):
            Link(left=INDOOR, right=_node('サイディング', 0.0, 0.002, 0), interface=_interface(22.4))

    def test_outdoor_on_right(self):
        with pytest.raises(ValueError, match='right'):
            Link(left=_node('石膏ボード', 0.00525, 0.0, 6), right=OUTDOOR, interface=_interface(9.2))

    def test_surface_without_interface(self):
        with pytest.raises(ValueError, match='表面の伝達'):
            Link(left=OUTDOOR, right=_node('サイディング', 0.0, 0.002, 0), interface=None)

    def test_same_layer_with_interface(self):
        a, b = _node('構造用合板1', 0.0009, 0.0009, 0), _node('構造用合板1', 0.0009, 0.0009, 0)
        with pytest.raises(ValueError, match='同じ層'):
            Link(left=a, right=b, interface=_interface(50.0))

    def test_different_layers_without_interface(self):
        a, b = _node('構造用合板1', 0.0009, 0.0, 0), _node('グラスウール1', 0.0, 0.0125, 1)
        with pytest.raises(ValueError, match='間のつながり'):
            Link(left=a, right=b, interface=None)

    def test_frozen(self):
        link = Link(left=OUTDOOR, right=_node('サイディング', 0.0, 0.002, 0), interface=_interface(22.4))
        with pytest.raises(dataclasses.FrozenInstanceError):
            link.interface = None


def _lambda(name: str) -> float:
    """旧 Excel の材料の熱伝導率, W/(m K)。"""
    return material_finder()('whamcavity', name).lambda_h


def _main_wall_interfaces() -> tuple:
    """今の main.py・Fortran の入力の壁の境目 8 個（外表面、通気層の両側、接触、防湿層、内表面）。"""
    return tuple(InterfaceInput(cond_h=h, cond_m=w) for h, w in (
        (22.4, 2.0e-11), (9.2, 3.43e-8), (9.2, 3.43e-8), (50.0, 7.75e-7),
        (50.0, 7.75e-7), (50.0, 2.0e-11), (50.0, 7.75e-7), (9.2, 2.6e-10),
    ))


class TestMakeLinks:

    def test_one_layer_total(self):
        # 合板 9 mm・分割数 6：つながり 7 個、熱抵抗の合計 = 1/22.4 + 0.009/λ + 1/9.2
        nodes = _make_nodes((_layer('構造用合板1', 0.009, 6),), find_material=material_finder())
        links = _make_links(nodes, (_interface_input(22.4), _interface_input(9.2)))
        assert len(links) == 7
        assert sum(l.r_h for l in links) == pytest.approx(1 / 22.4 + 0.009 / _lambda('構造用合板1') + 1 / 9.2)

    def test_two_layers_total(self):
        # 合板 9 mm + GW 100 mm、接触 50：接触抵抗 1/50 が 1 回だけ入る
        layers = (_layer('構造用合板1', 0.009, 6), _layer('グラスウール1', 0.1, 5))
        nodes = _make_nodes(layers, find_material=material_finder())
        links = _make_links(nodes, (_interface_input(22.4), _interface_input(50.0), _interface_input(9.2)))
        expected = 1 / 22.4 + 0.009 / _lambda('構造用合板1') + 1 / 50.0 + 0.1 / _lambda('グラスウール1') + 1 / 9.2
        assert sum(l.r_h for l in links) == pytest.approx(expected)

    def test_air_layer_total(self):
        # サイディング + 通気層 + 石膏ボード：通気層の両側は 1/9.2、空気の中の抵抗は 0
        layers = (_layer('サイディング', 0.016, 5), _air_layer(), _layer('石膏ボード', 0.042, 5))
        nodes = _make_nodes(layers, find_material=material_finder())
        links = _make_links(nodes, (_interface_input(22.4), _interface_input(9.2), _interface_input(9.2), _interface_input(9.2)))
        expected = 1 / 22.4 + 0.016 / _lambda('サイディング') + 1 / 9.2 + 1 / 9.2 + 0.042 / _lambda('石膏ボード') + 1 / 9.2
        assert sum(l.r_h for l in links) == pytest.approx(expected)

    def test_main_wall_number(self):
        # 今の壁 7 層・質点 33 個：つながり 34 個
        nodes = _make_nodes(_main_wall_layers(), find_material=material_finder())
        assert len(_make_links(nodes, _main_wall_interfaces())) == 34

    def test_each_interface_used_once(self):
        # 境目を持つつながりは 8 個で、入力の境目の 8 個が外気側から順に 1 回ずつ、抵抗（1 / コンダクタンス）に変えて使われる
        interfaces = _main_wall_interfaces()
        nodes = _make_nodes(_main_wall_layers(), find_material=material_finder())
        used = [l.interface for l in _make_links(nodes, interfaces) if l.interface is not None]
        assert len(used) == 8
        assert [(u.r_h, u.r_m) for u in used] == pytest.approx([(1 / x.cond_h, 1 / x.cond_m) for x in interfaces])

    def test_order(self):
        # k 番目のつながりは、質点 k - 1 と質点 k の間。両端は外気と室内
        nodes = _make_nodes(_main_wall_layers(), find_material=material_finder())
        links = _make_links(nodes, _main_wall_interfaces())
        assert links[0].left is OUTDOOR and links[0].right is nodes[0]
        assert links[-1].left is nodes[-1] and links[-1].right is INDOOR
        for k in range(1, len(nodes)):
            assert links[k].left is nodes[k - 1] and links[k].right is nodes[k]


def _state(rh: float) -> State:
    """20 deg.C・相対湿度 rh % の状態。"""
    return State.init(t=20.0 + ATP, rh=rh)


def _interface_m(cond_m: float) -> Interface:
    """湿気コンダクタンス cond_m の境目（熱は 50）。計算の側の境目なので抵抗で持つ。"""
    return Interface(r_h=1.0 / 50.0, r_m=1.0 / cond_m)


class TestLinkMoisture:

    def test_interior(self):
        # 合板の中、左右とも RH 50%：0.0018 / 湿気伝導率(50%)
        a, b = _node('構造用合板1', 0.0009, 0.0009, 0), _node('構造用合板1', 0.0009, 0.0009, 0)
        link = Link(left=a, right=b, interface=None)
        s = _state(50.0)
        assert link.r_m(s, s) == pytest.approx(0.0018 / a.material.get_lambda_dsh_m(rh=s.rh))

    def test_interior_different_states(self):
        # 左 RH 50%・右 RH 90%：左右の半分は、それぞれの側の状態で計算する
        a, b = _node('構造用合板1', 0.0009, 0.0009, 0), _node('構造用合板1', 0.0009, 0.0009, 0)
        link = Link(left=a, right=b, interface=None)
        s50, s90 = _state(50.0), _state(90.0)
        m = a.material
        assert link.r_m(s50, s90) == pytest.approx(0.0009 / m.get_lambda_dsh_m(rh=s50.rh) + 0.0009 / m.get_lambda_dsh_m(rh=s90.rh))

    @pytest.mark.parametrize('cond_m', [7.75e-7, 2.0e-11])
    def test_layer_to_layer(self, cond_m):
        # 合板の右の端と GW の左の端：境目の 1 / cond_m だけ（接触 7.75e-7、防湿層 2.0e-11）
        a, b = _node('構造用合板1', 0.0009, 0.0, 0), _node('グラスウール1', 0.0, 0.0125, 1)
        link = Link(left=a, right=b, interface=_interface_m(cond_m))
        s = _state(50.0)
        assert link.r_m(s, s) == pytest.approx(1 / cond_m)

    def test_outside_surface(self):
        link = Link(left=OUTDOOR, right=_node('サイディング', 0.0, 0.002, 0), interface=_interface_m(2.0e-11))
        s = _state(50.0)
        assert link.r_m(s, s) == pytest.approx(1 / 2.0e-11)

    def test_inside_surface(self):
        link = Link(left=_node('石膏ボード', 0.00525, 0.0, 6), right=INDOOR, interface=_interface_m(2.6e-10))
        s = _state(50.0)
        assert link.r_m(s, s) == pytest.approx(1 / 2.6e-10)

    def test_air_layer(self):
        air = AirNode(thickness=0.025, alpha=0.085, layer_index=1)
        link = Link(left=_node('サイディング', 0.002, 0.0, 0), right=air, interface=_interface_m(3.43e-8))
        s = _state(50.0)
        assert link.r_m(s, s) == pytest.approx(1 / 3.43e-8)


class TestLinkLiquid:

    def test_interface(self):
        # 境目のあるつながりは、液水は移動しない（無限大）
        a, b = _node('構造用合板1', 0.0009, 0.0, 0), _node('グラスウール1', 0.0, 0.0125, 1)
        link = Link(left=a, right=b, interface=_interface_m(7.75e-7))
        s = _state(99.0)
        assert link.r_l(s, s) == float('inf')

    def test_interior_no_liquid(self):
        # 構造用合板1 は RH 50% では液水伝導率 0：無限大
        a, b = _node('構造用合板1', 0.0009, 0.0009, 0), _node('構造用合板1', 0.0009, 0.0009, 0)
        link = Link(left=a, right=b, interface=None)
        s = _state(50.0)
        assert link.r_l(s, s) == float('inf')

    def test_interior_liquid(self):
        # 構造用合板1 は RH 99% では液水が動く：0.0018 / 液水伝導率
        a, b = _node('構造用合板1', 0.0009, 0.0009, 0), _node('構造用合板1', 0.0009, 0.0009, 0)
        link = Link(left=a, right=b, interface=None)
        s = _state(99.0)
        lambda_l = a.material.get_lambda_dsh_mu_l(rh=s.rh, t=s.t)
        assert lambda_l > 0.0
        assert link.r_l(s, s) == pytest.approx(0.0018 / lambda_l)


class TestInterface:

    def test_values(self):
        interface = Interface(r_h=1 / 50.0, r_m=1 / 7.75e-7)
        assert (interface.r_h, interface.r_m) == (1 / 50.0, 1 / 7.75e-7)

    @pytest.mark.parametrize('r_h, r_m, key', [(0.0, 1.0e6, 'r_h'), (0.02, -1.0, 'r_m')])
    def test_invalid_value(self, r_h, r_m, key):
        with pytest.raises(ValueError, match=key):
            Interface(r_h=r_h, r_m=r_m)

    def test_frozen(self):
        interface = Interface(r_h=1 / 50.0, r_m=1 / 7.75e-7)
        with pytest.raises(dataclasses.FrozenInstanceError):
            interface.r_h = 0.1


class TestSurface:

    def test_values(self):
        surface = Surface(direction=Direction.E, angle=90.0, albedo=0.3, absorptance=0.9, emissivity=0.9, eva_height=4.2)
        assert surface.direction == Direction.E
        assert (surface.angle, surface.albedo, surface.absorptance, surface.emissivity, surface.eva_height) == (90.0, 0.3, 0.9, 0.9, 4.2)

    def test_frozen(self):
        surface = Surface(direction=Direction.E, angle=90.0, albedo=0.3, absorptance=0.9, emissivity=0.9, eva_height=4.2)
        with pytest.raises(dataclasses.FrozenInstanceError):
            surface.angle = 45.0
