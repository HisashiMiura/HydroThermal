"""壁の組み立て：壁の入力から、壁の形と初期の状態を一緒に作る（入力から計算への橋渡し）。

入力のクラス（wall_input）と計算の側の部品（wall_geometry・wall_state）の両方を知っているのは、ここ（と WallGeometry.from_input）だけ。
水膜・木材腐朽の状態の初期値も、作るときにここに足す（段階 7）。
"""

import numpy as np

from modules.thermo_dynamics import ATP, get_wp
from modules.wall_geometry import FindMaterial, WallGeometry
from modules.wall_input import WallInput
from modules.wall_state import WallState


def build_wall(wall_input: WallInput, find_material: FindMaterial | None = None) -> tuple[WallGeometry, WallState]:
    """壁の入力から、壁の形と初期の状態を一緒に作る。

    各質点の初期の温度・相対湿度は、その質点の層（layer_index）の入力の初期値にする（Fortran の TPINT・RHINT と同じ）。
    壁の形と初期の状態を同じ壁の入力から作るので、質点と層の対応は必ず合う。

    Args:
        wall_input: 壁の入力（確かめ済み）
        find_material: 材料を探す関数。渡さなければ、Excel から探す（material_finder()）

    Returns:
        壁の形、初期の状態
    """

    geometry = WallGeometry.from_input(wall_input, find_material)

    layers = wall_input.layers

    # 各質点の初期の温度, K, [i]（その質点の層の初期の温度）
    t_is = np.array([layers[node.layer_index].initial_temperature + ATP for node in geometry.nodes])

    # 各質点の初期の水分化学ポテンシャル, J/kg, [i]（その質点の層の初期の相対湿度と、温度から）
    mu_is = np.array([get_wp(rh=layers[node.layer_index].initial_rh, t=t_i) for node, t_i in zip(geometry.nodes, t_is)])

    return geometry, WallState(t_is=t_is, mu_is=mu_is)
