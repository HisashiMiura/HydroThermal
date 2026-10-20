import pytest


from modules.cell import CellInterior
from modules.materials import Materials
from modules.material_loaders import load_whamcavity
from modules.state import State
from modules.thermo_dynamics import get_dpv_dmu
from modules import material_loaders
from modules.materials import Material
from modules.wall import Wall, Layer, get_materials_of_layers


_whamcavity = Materials(load_whamcavity())


def _wall_with_cells(cells):
    """セルの一覧だけを持つ Wall を作る（係数の計算は cells_is しか使わないため、ほかの項目は作らない）。"""

    wall = object.__new__(Wall)
    wall.cells_is = cells
    return wall


# 構造用合板1 の 3 つのセル（幅 1 cm, 2 cm, 3 cm）。真ん中（i = 1）の両側の係数を確かめる。
_plywood1 = _whamcavity.get_material('構造用合板1')
_cells = [CellInterior(x=0.01, material=_plywood1), CellInterior(x=0.02, material=_plywood1), CellInterior(x=0.03, material=_plywood1)]

# 湿度の違う 3 つの状態（温度 20 ℃、相対湿度 30%, 60%, 90%）
_states = [State.init(t=293.15, rh=rh) for rh in (30.0, 60.0, 90.0)]


def _expected(cell_a, state_a, cell_b, state_b, side_a, side_b):
    """1 / (透湿抵抗 ÷ dpv/dμ の和) を、セルの幅と湿気伝導率から手で計算する。

    side_a, side_b: そのセルの半分のうち境目側の半分の幅の割合（CellInterior は 1/2）
    """

    r_a = cell_a.x * side_a / cell_a.material.get_lambda_dsh_m(rh=state_a.rh)
    r_b = cell_b.x * side_b / cell_b.material.get_lambda_dsh_m(rh=state_b.rh)

    return 1 / (r_a / get_dpv_dmu(rh=state_a.rh, t=state_a.t) + r_b / get_dpv_dmu(rh=state_b.rh, t=state_b.t))


def test_c_vap_wp_i_mns():
    """室外側の係数が、透湿抵抗から求めた値になることを確認する（熱抵抗を使っていないこと）。"""

    wall = _wall_with_cells(_cells)

    c = wall._c_vap_wp_i_mns(i=1, state=_states[1], state_mns=_states[0])

    assert c == pytest.approx(_expected(_cells[0], _states[0], _cells[1], _states[1], 0.5, 0.5), rel=1e-12)


def test_c_vap_wp_i_pls():
    """室内側の係数が、透湿抵抗から求めた値になることを確認する（熱抵抗を使っていないこと）。"""

    wall = _wall_with_cells(_cells)

    c = wall._c_vap_wp_i_pls(i=1, state=_states[1], state_pls=_states[2])

    assert c == pytest.approx(_expected(_cells[2], _states[2], _cells[1], _states[1], 0.5, 0.5), rel=1e-12)


def test_c_vap_wp_order_of_magnitude():
    """係数の大きさが、熱抵抗を使っていたとき（約 0.1）ではなく、透湿抵抗のもの（10^-12 程度）であることを確認する。"""

    wall = _wall_with_cells(_cells)

    c = wall._c_vap_wp_i_mns(i=1, state=_states[1], state_mns=_states[0])

    assert c < 1e-9


def test_c_liq_wp_no_liquid():
    """液水が移動しない材料（グラスウール1）の間では、液水の係数が 0 になる（0 で割るエラーにならない）ことを確認する。"""

    glass_wool = _whamcavity.get_material('グラスウール1')
    wall = _wall_with_cells([CellInterior(x=0.01, material=glass_wool) for _ in range(3)])

    assert wall._c_liq_wp_i_mns(i=1, state=_states[1], state_mns=_states[0]) == 0.0
    assert wall._c_liq_wp_i_pls(i=1, state=_states[1], state_pls=_states[2]) == 0.0


def test_c_liq_wp_one_side_no_liquid():
    """片側だけ液水が移動しない（構造用合板1 の RH 99% と グラスウール1）とき、液水の係数が 0 になることを確認する。"""

    glass_wool = _whamcavity.get_material('グラスウール1')
    wall = _wall_with_cells([CellInterior(x=0.01, material=glass_wool), CellInterior(x=0.01, material=_plywood1)])
    state_99 = State.init(t=293.15, rh=99.0)

    assert wall._c_liq_wp_i_mns(i=1, state=state_99, state_mns=_states[1]) == 0.0


def _layer(name: str, source: str | None = None) -> Layer:
    """材料を探すテスト用の層を作る（材料の出どころと名称以外は使わないので適当な値）。"""

    kwargs = {} if source is None else {'source': source}

    return Layer(
        num=0, name=name, initial_temp=20.0, initial_humidity=60.0, thick=0.01, n_div=1,
        cond_h_o=9.2, cond_h_i=9.2, cond_m_o=3.43E-08, cond_m_i=3.43E-08, alpha=0.0, **kwargs)


def test_get_materials_of_layers():
    """層ごとに、出どころと名称で材料が探せることを確認する。出どころを省略すると旧 Excel になる。"""

    layers = [
        _layer('サイディング'),
        _layer('ASHRAE Plywood -1', source='mews_ashrae'),
        _layer('構造用合板1', source='whamcavity'),
    ]

    ms = get_materials_of_layers(layers=layers)

    assert [m.name for m in ms] == ['サイディング', 'ASHRAE Plywood -1', '構造用合板1']
    assert ms[1].rho == 445.0
    assert ms[2].rho == 600.0


def test_get_materials_of_layers_same_name(monkeypatch):
    """出どころが違えば、同じ名称の材料があっても区別できることを確認する。

    同じ名称「合板」で密度だけが違う材料を返す、2つのテスト用の出どころを使う。
    """

    plywood = _whamcavity.get_material('構造用合板1')

    def loader(rho):
        return lambda: [Material(
            name='合板', lambda_h=plywood.lambda_h, c=plywood.c, rho=rho, isotherm=plywood.isotherm,
            vapor_conductivity=plywood.vapor_conductivity, liquid_diffusivity=plywood.liquid_diffusivity)]

    monkeypatch.setitem(material_loaders.MATERIAL_SOURCES, 'source_a', loader(500.0))
    monkeypatch.setitem(material_loaders.MATERIAL_SOURCES, 'source_b', loader(700.0))

    ms = get_materials_of_layers(layers=[_layer('合板', source='source_a'), _layer('合板', source='source_b')])

    assert [m.rho for m in ms] == [500.0, 700.0]


def test_get_materials_of_layers_unknown_source():
    """層の出どころの名前を間違えたとき、ValueError になることを確認する。"""

    with pytest.raises(ValueError, match='出どころ'):
        get_materials_of_layers(layers=[_layer('サイディング', source='mews')])
