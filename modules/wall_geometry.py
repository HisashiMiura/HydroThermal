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
from modules.state import State
from modules.thermo_dynamics import ROW_CP
from modules.wall_input import AirLayerInput, InterfaceInput, LayerInput


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

    def r_m_left(self, state: State) -> float:
        """質点から左（外気側）の端までの透湿抵抗, (m2 s Pa)/kg（その状態の相対湿度での湿気伝導率を使う）"""
        return self.d_left / self.material.get_lambda_dsh_m(rh=state.rh)

    def r_m_right(self, state: State) -> float:
        """質点から右（室内側）の端までの透湿抵抗, (m2 s Pa)/kg（その状態の相対湿度での湿気伝導率を使う）"""
        return self.d_right / self.material.get_lambda_dsh_m(rh=state.rh)

    def r_l_left(self, state: State) -> float:
        """質点から左（外気側）の端までの液水の抵抗, (m2 s (J/kg))/kg"""
        return self._r_l(self.d_left, state)

    def r_l_right(self, state: State) -> float:
        """質点から右（室内側）の端までの液水の抵抗, (m2 s (J/kg))/kg"""
        return self._r_l(self.d_right, state)

    def _r_l(self, d: float, state: State) -> float:
        """距離 d の液水の抵抗, (m2 s (J/kg))/kg。

        液水伝導率が 0（液水が移動しない材料、または液水拡散係数の範囲の外）なら、0 で割らずに無限大にする。
        """

        lambda_l = self.material.get_lambda_dsh_mu_l(rh=state.rh, t=state.t)

        # 液水伝導率が 0 なら無限大（液水は移動しない）
        return float('inf') if lambda_l == 0.0 else d / lambda_l


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

    def r_m_left(self, state: State) -> float:
        """質点から左の端までの透湿抵抗, (m2 s Pa)/kg（よく混ざった空気なので 0）"""
        return 0.0

    def r_m_right(self, state: State) -> float:
        """質点から右の端までの透湿抵抗, (m2 s Pa)/kg（よく混ざった空気なので 0）"""
        return 0.0


# 質点：材料の質点か空気の質点のどちらか
Node = MaterialNode | AirNode


@dataclass(frozen=True)
class Outdoor:
    """外気。つながりの左（外気側）の端になる。

    質点ではないので、端までの抵抗は 0（外表面の伝達は、つながりの境目が持つ）。
    外気の温度・湿度は、時刻ごとの境界条件から取り出す（段階 6）。
    """

    @property
    def r_h_right(self) -> float:
        """右の端までの熱抵抗, (m2 K)/W（質点ではないので 0）"""
        return 0.0

    def r_m_right(self, state: State) -> float:
        """右の端までの透湿抵抗, (m2 s Pa)/kg（質点ではないので 0）"""
        return 0.0


@dataclass(frozen=True)
class Indoor:
    """室内。つながりの右（室内側）の端になる。

    質点ではないので、端までの抵抗は 0（内表面の伝達は、つながりの境目が持つ）。
    室内の温度・湿度は、時刻ごとの境界条件から取り出す（段階 6）。
    """

    @property
    def r_h_left(self) -> float:
        """左の端までの熱抵抗, (m2 K)/W（質点ではないので 0）"""
        return 0.0

    def r_m_left(self, state: State) -> float:
        """左の端までの透湿抵抗, (m2 s Pa)/kg（質点ではないので 0）"""
        return 0.0


# 外気と室内（値を持たないので、1 つずつ作って使い回す）
OUTDOOR = Outdoor()
INDOOR = Indoor()


@dataclass(frozen=True, kw_only=True)
class Interface:
    """計算の側の境目：表面の伝達、層と層の接触、材料と通気層の間の伝達、塗膜・防湿層などの抵抗。

    入力の境目（wall_input.InterfaceInput、コンダクタンス）から、_make_links で作る。
    境目では液水は移動しない。
    """

    # 熱抵抗, (m2 K)/W
    r_h: float

    # 透湿抵抗, (m2 s Pa)/kg
    r_m: float

    def __post_init__(self):
        """作るときに値を確かめる。"""

        # 熱抵抗・透湿抵抗が 0 より大きくなければエラー
        for key in ('r_h', 'r_m'):
            value = getattr(self, key)
            if not value > 0.0:
                raise ValueError(f'境目の {key} は 0 より大きくしてください（{value}）。')


@dataclass(frozen=True, kw_only=True)
class Link:
    """つながり：隣り合う 2 つの質点、または端の質点と外気・室内の間。

    抵抗 = 左から右の端までの抵抗 + 境目の抵抗 + 右から左の端までの抵抗。
    層の中のつながりは境目を持たない。層と層・材料と通気層・表面のつながりは、境目（Interface）を持つ。
    """

    # 左（外気側）：質点か外気
    left: Node | Outdoor

    # 右（室内側）：質点か室内
    right: Node | Indoor

    # 境目。層の中のつながりは None（境目がない）
    interface: Interface | None

    def __post_init__(self):
        """作るときに、つながりの形を確かめる。"""

        # 左が質点か外気でなければエラー（室内を左に置くことはできない）
        if not isinstance(self.left, (MaterialNode, AirNode, Outdoor)):
            raise ValueError(f'つながりの左 left は、質点か外気にしてください（{type(self.left).__name__}）。')

        # 右が質点か室内でなければエラー（外気を右に置くことはできない）
        if not isinstance(self.right, (MaterialNode, AirNode, Indoor)):
            raise ValueError(f'つながりの右 right は、質点か室内にしてください（{type(self.right).__name__}）。')

        # 外気・室内に面するつながりに境目がなければエラー（表面の伝達を境目で表すため）
        if isinstance(self.left, Outdoor) or isinstance(self.right, Indoor):
            if self.interface is None:
                raise ValueError('外気・室内に面するつながりには、境目 interface（表面の伝達）が必要です。')
            return

        # 左右がどちらも質点のとき、同じ層なら境目なし、違う層なら境目ありでなければエラー
        same_layer = self.left.layer_index == self.right.layer_index
        if same_layer and self.interface is not None:
            raise ValueError(f'同じ層（{self.left.layer_index} 番目）の中のつながりに、境目 interface は指定できません。')
        if not same_layer and self.interface is None:
            raise ValueError(f'層 {self.left.layer_index} 番目と {self.right.layer_index} 番目の間のつながりには、境目 interface が必要です。')

    @property
    def r_h(self) -> float:
        """熱抵抗, (m2 K)/W"""

        # 境目の熱抵抗（層の中なら 0）
        r_interface = self.interface.r_h if self.interface is not None else 0.0

        # 左から右の端まで ＋ 境目 ＋ 右から左の端まで（外気・室内・空気の質点の分は 0）
        return self.left.r_h_right + r_interface + self.right.r_h_left

    def r_m(self, state_left: State, state_right: State) -> float:
        """透湿抵抗, (m2 s Pa)/kg

        左右の半分は、それぞれの側の状態（相対湿度）で計算する。外気・室内の側には、外気・室内の状態を渡す（使わないが、渡し方をそろえる）。

        Args:
            state_left: 左（質点か外気）の状態
            state_right: 右（質点か室内）の状態
        """

        # 境目の透湿抵抗（層の中なら 0）
        r_interface = self.interface.r_m if self.interface is not None else 0.0

        # 左から右の端まで ＋ 境目 ＋ 右から左の端まで（外気・室内・空気の質点の分は 0）
        return self.left.r_m_right(state_left) + r_interface + self.right.r_m_left(state_right)

    def r_l(self, state_left: State, state_right: State) -> float:
        """液水の抵抗, (m2 s (J/kg))/kg

        境目（層と層、材料と通気層、表面）では液水は移動しないので無限大。層の中だけ、左右の材料の質点の液水の抵抗を足す。

        Args:
            state_left: 左の状態
            state_right: 右の状態
        """

        # 境目のあるつながりなら無限大（境目では液水は移動しない）
        if self.interface is not None:
            return float('inf')

        # 層の中（左右とも同じ層の材料の質点）
        return self.left.r_l_right(state_left) + self.right.r_l_left(state_right)


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


def _make_links(nodes: tuple[Node, ...], interfaces: tuple[InterfaceInput, ...]) -> tuple[Link, ...]:
    """質点の並びと境目の並びから、つながりの並び（外気側から順、質点の数 + 1 個）を作る。

    k 番目のつながりは、質点 k - 1 と質点 k の間（0 番目は外気と質点 0、最後は最後の質点と室内）。
    j 番目の境目は、層 j - 1 と層 j の間（0 番目は外表面、最後は内表面）。

    内部用の関数。ふだんは WallGeometry.from_input から、_make_nodes で作った質点と WallInput の interfaces を渡して呼ぶ。
    正しく作れているかは、Link を作るときの確認（境目の有無と層の関係）でも確かめられる。

    Args:
        nodes: 質点の並び（_make_nodes で作ったもの）
        interfaces: 入力の境目の並び（WallInput.interfaces。層の数 + 1 個）。計算の側の境目（Interface）に変えて使う
    """

    # 入力の境目（コンダクタンス）を、計算の側の境目（抵抗）に変える
    ifs = [Interface(r_h=1.0 / x.cond_h, r_m=1.0 / x.cond_m) for x in interfaces]

    # 外気と最初の質点（外表面）
    links = [Link(left=OUTDOOR, right=nodes[0], interface=ifs[0])]

    # 隣り合う質点どうし（0 番目と 1 番目、1 番目と 2 番目、…）
    for left, right in zip(nodes[:-1], nodes[1:]):

        # 同じ層の中なら境目なし、層が変わるところなら右の層の手前の境目（層 i と層 i + 1 の間は ifs[i + 1]）
        interface = None if left.layer_index == right.layer_index else ifs[right.layer_index]

        links.append(Link(left=left, right=right, interface=interface))

    # 最後の質点と室内（内表面）
    links.append(Link(left=nodes[-1], right=INDOOR, interface=ifs[-1]))

    return tuple(links)
