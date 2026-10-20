import pytest


from modules.cell import CellInterior
from modules.materials import Materials
from modules.material_loaders import load_whamcavity
from modules.state import State
from modules.thermo_dynamics import get_dpv_dmu
from modules.wall import Wall


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
