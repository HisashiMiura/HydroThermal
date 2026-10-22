"""壁の形（時間で変わらないもの）：質点とつながり。

壁の入力（wall_input.WallInput）から作る。段階 2（docs/design/class_structure.md）で作る。
今の cell.py・wall.py の Cell と質点の配列は、置き換えが終わったら消す。

質点の置き方（設計の文書 2.3 節）：層の両端（表面・異種材料の境目）に必ず質点を置く。
層の中の質点はコントロールボリュームの中心にあり、層の端の質点は表面・境目の上にある。

つながりは、質点に「質点からコントロールボリュームの端までの抵抗」を聞いて、境目の抵抗と足す。
材料の質点と空気の質点は、同じ名前（width・heat_capacity・r_h_left・r_h_right・layer_index）で使える。
"""

from collections.abc import Callable
from dataclasses import dataclass

from modules.material_loaders import load_materials
from modules.materials import Material, Materials
from modules.thermo_dynamics import ROW_CP
from modules.wall_input import AirLayerInput, LayerInput


@dataclass(frozen=True, kw_only=True)
class MaterialNode:
    """材料の質点。"""

    # 質点からコントロールボリュームの左（外気側）の端までの距離, m（層の左の端の質点は 0）
    d_left: float

    # 質点からコントロールボリュームの右（室内側）の端までの距離, m（層の右の端の質点は 0）
    d_right: float

    # 材料
    material: Material

    # どの層の質点か（外気側から 0, 1, 2, …）
    layer_index: int

    def __post_init__(self):
        """作るときに値を確かめる。"""

        # 左右の端までの距離が 0 以上でなければエラー（層の端の質点は、表面・境目の側が 0）
        if not (self.d_left >= 0.0 and self.d_right >= 0.0):
            raise ValueError(f'左右の端までの距離 d_left・d_right は 0 以上にしてください（{self.d_left}, {self.d_right}）。')

        # 幅（左右の距離の和）が 0 より大きくなければエラー
        if not self.width > 0.0:
            raise ValueError(f'質点の幅（d_left + d_right）は 0 より大きくしてください（{self.width}）。')

    @property
    def width(self) -> float:
        """コントロールボリュームの幅, m（左右の端までの距離の和）"""
        return self.d_left + self.d_right

    @property
    def heat_capacity(self) -> float:
        """熱容量, J/(m2 K)（幅 × 容積比熱）"""
        return self.width * self.material.c_rho

    @property
    def r_h_left(self) -> float:
        """質点から左（外気側）の端までの熱抵抗, (m2 K)/W"""
        return self.d_left / self.material.lambda_h

    @property
    def r_h_right(self) -> float:
        """質点から右（室内側）の端までの熱抵抗, (m2 K)/W"""
        return self.d_right / self.material.lambda_h


@dataclass(frozen=True, kw_only=True)
class AirNode:
    """通気層の空気の質点（よく混ざった空気の 1 つの質点）。

    空気はよく混ざっているとみなし、質点から端までの抵抗は 0。
    材料と通気層の間の伝達は、つながりの境目の抵抗が持つ。
    """

    # 通気層の厚さ, m
    thickness: float

    # 流量係数, -（相当開口面積 = α × 厚さ × 壁の横の長さ。壁 1 m2 あたりの換気量では横の長さが消えるので、α のまま持つ）
    alpha: float

    # どの層の質点か（外気側から 0, 1, 2, …）
    layer_index: int

    def __post_init__(self):
        """作るときに値を確かめる。"""

        # 厚さが 0 より大きくなければエラー
        if not self.thickness > 0.0:
            raise ValueError(f'通気層の厚さ thickness は 0 より大きくしてください（{self.thickness}）。')

        # 流量係数が 0 以上でなければエラー（0 は換気のない空気層）
        if not self.alpha >= 0.0:
            raise ValueError(f'流量係数 alpha は 0 以上にしてください（{self.alpha}）。')

    @property
    def width(self) -> float:
        """コントロールボリュームの幅, m（通気層の厚さ）"""
        return self.thickness

    @property
    def heat_capacity(self) -> float:
        """熱容量, J/(m2 K)（厚さ × 空気の容積比熱）"""
        return self.thickness * ROW_CP

    @property
    def r_h_left(self) -> float:
        """質点から左の端までの熱抵抗, (m2 K)/W（よく混ざった空気なので 0）"""
        return 0.0

    @property
    def r_h_right(self) -> float:
        """質点から右の端までの熱抵抗, (m2 K)/W（よく混ざった空気なので 0）"""
        return 0.0


# 質点：材料の質点か空気の質点のどちらか
Node = MaterialNode | AirNode


# 材料を探す関数：(出どころ, 名称) → 材料
FindMaterial = Callable[[str, str], Material]


def material_finder() -> FindMaterial:
    """Excel から材料を探す関数を作る。出どころごとに、最初に使うときに 1 回だけ読み込む。

    例:
        find = material_finder()
        find('whamcavity', '構造用合板1')
    """

    # 出どころごとの材料の一覧（読み込んだものを覚えておく）
    materials_by_source: dict[str, Materials] = {}

    def find(source: str, name: str) -> Material:

        # まだ読み込んでいない出どころなら、読み込んで覚えておく
        if source not in materials_by_source:
            materials_by_source[source] = Materials(load_materials(source))

        return materials_by_source[source].get_material(name=name)

    return find


def _make_nodes(layers: tuple[LayerInput, ...], find_material: FindMaterial) -> tuple[Node, ...]:
    """層の並び（外気側から順）から、質点の並び（外気側から順）を作る。

    材料の層（厚さ d、分割数 n）は、間隔 dx = d / (n - 1) で n 個の質点にする。層の両端の質点は表面・境目の上にあり、
    その側までの距離は 0、内側の端までの距離は dx / 2。層の中の質点は、左右とも dx / 2。
    通気層は、空気の質点 1 つにする。

    内部用の関数。ふだんは WallGeometry.from_input から、WallInput の layers を渡して呼ぶ。
    いちばん外側・いちばん内側が材料の層であること、通気層が 2 枚続かないことなどは WallInput で確かめ済みなので、ここでは確かめない。

    Args:
        layers: 層の入力の並び（WallInput.layers）
        find_material: 材料を探す関数（ふだんは material_finder() で作る）
    """

    nodes: list[Node] = []

    for i, layer in enumerate(layers):

        # 通気層なら、空気の質点を 1 つ作る
        if isinstance(layer, AirLayerInput):
            nodes.append(AirNode(thickness=layer.thickness, alpha=layer.alpha, layer_index=i))
            continue

        # 材料の層なら、材料を探す。見つからなければ（KeyError）、どの層かを付けてエラーにする
        try:
            material = find_material(layer.source, layer.name)
        except KeyError:
            raise ValueError(f'層 {i} 番目の材料が見つかりません（出どころ {layer.source!r}、名称 {layer.name!r}）。') from None

        # 質点の間隔, m（分割数は入力の確認で 2 以上なので、0 で割ることはない）
        dx = layer.thickness / (layer.n_div - 1)

        # 層の左の端・中・右の端の質点を作る（端の質点は、表面・境目の側までの距離が 0）
        for j in range(layer.n_div):
            d_left = 0.0 if j == 0 else dx / 2
            d_right = 0.0 if j == layer.n_div - 1 else dx / 2
            nodes.append(MaterialNode(d_left=d_left, d_right=d_right, material=material, layer_index=i))

    return tuple(nodes)
