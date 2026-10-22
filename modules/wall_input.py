"""壁の入力（確認済みの値だけを持つ部品）。

入力の dict から作り、値がそろっていておかしくないことを、作るときに 1 回だけ確かめる。
作ったあとは値を変えない（frozen）。計算する部品は、ここで確かめた値だけを受け取る。

段階 1（docs/design/class_structure.md）で作る。今の input_wall.py・wall.Layer は、置き換えが終わったら消す。
"""

from dataclasses import dataclass
from typing import Self

from modules.direction import Direction
from modules.material_loaders import MATERIAL_SOURCES


# 材料の層の入力の dict のキー（すべて必ず指定する）
_MATERIAL_LAYER_KEYS = ('source', 'name', 'thickness', 'n_div', 'initial_temperature', 'initial_rh')

# 通気層の入力の dict のキー（すべて必ず指定する。'air_layer' は True）
_AIR_LAYER_KEYS = ('air_layer', 'thickness', 'alpha', 'initial_temperature', 'initial_rh')

# 境目の入力の dict のキー（すべて必ず指定する）
_INTERFACE_KEYS = ('cond_h', 'cond_m')

# 外表面の入力の dict のキー（すべて必ず指定する）
_SURFACE_KEYS = ('direction', 'angle', 'albedo', 'absorptance', 'emissivity', 'eva_height')

# 壁の入力の dict のキー（すべて必ず指定する）
_WALL_KEYS = ('surface', 'layers', 'interfaces', 'len_vertical', 'len_horizontal', 'height')


def _check_keys(d: dict, required: tuple[str, ...], where: str):
    """dict のキーを確かめる。必ず指定するキーがない、または知らないキー（打ち間違いなど）があればエラーにする。

    Args:
        d: 入力の dict
        required: 必ず指定するキー（これ以外のキーは使えない）
        where: エラーのメッセージに出す、どの入力か
    """

    # 必ず指定するキーのうち、dict にないものを集める。1 つでもあればエラー
    missing = [k for k in required if k not in d]
    if missing:
        raise ValueError(f'{where} に {missing} がありません。')

    # dict のキーのうち、使えるキーにないもの（打ち間違いなど）を集める。1 つでもあればエラー
    unknown = sorted(set(d) - set(required))
    if unknown:
        raise ValueError(f'{where} に知らないキー {unknown} があります（使えるキー: {list(required)}）。')


def _from_dict_at(from_dict, d, at: str):
    """入れ子の入力を from_dict で作る。エラーのときは、どこの入力か（at）をメッセージの頭に付ける。

    Args:
        from_dict: 部品を dict から作る関数（SurfaceInput.from_dict など）
        d: 入力の dict
        at: どこの入力か（'layers の 2 番目' など）
    """

    # dict でなければエラー
    if not isinstance(d, dict):
        raise ValueError(f'壁の入力の {at} は dict で書いてください（{type(d).__name__}）。')

    # 部品を作る。エラーなら、どこの入力かを頭に付けて出し直す
    try:
        return from_dict(d)
    except ValueError as e:
        raise ValueError(f'壁の入力の {at}: {e}') from None


@dataclass(frozen=True, kw_only=True)
class MaterialLayerInput:
    """材料の層 1 枚分の入力。

    層と層・層と空気の境目の値（接触・表面のコンダクタンス）は、ここではなく境目の入力が持つ。
    """

    # 材料の出どころ（material_loaders.MATERIAL_SOURCES のキー）
    source: str

    # 材料の名称
    name: str

    # 厚さ, m
    thickness: float

    # 分割数（質点の数）。層の両端に質点を置く
    n_div: int

    # 初期の温度, deg.C
    initial_temperature: float

    # 初期の相対湿度, %
    initial_rh: float

    def __post_init__(self):
        """作るときに値を確かめる（直接作っても、from_dict で作っても働く）。

        材料の名称が実際にその出どころにあるかは、材料を読み込むとき（壁の形を作るとき）に確かめる。
        初期の温度は決まった範囲がないので確かめない。
        """

        # 出どころが、材料を読み込める Excel（'whamcavity'・'mews_ashrae'）のどれかでなければエラー
        if self.source not in MATERIAL_SOURCES:
            raise ValueError(f'材料の出どころ source は {list(MATERIAL_SOURCES)} のどれかにしてください（{self.source!r}）。')

        # 名称が文字列でない、または空の文字列ならエラー
        if not isinstance(self.name, str) or self.name == '':
            raise ValueError(f'材料の名称 name を指定してください（{self.name!r}）。')

        # 厚さが 0 より大きくなければエラー
        # （「not ... > 0」と書くのは、数値でない値（NaN など）も「0 より大きい」にならず、エラーになるようにするため）
        if not self.thickness > 0.0:
            raise ValueError(f'厚さ thickness は 0 より大きくしてください（{self.thickness}）。')

        # 分割数が、真偽値（True・False）、整数でない値、2 より小さい値のどれかならエラー
        # （真偽値を先に除くのは、Python では True・False が整数の 1・0 として扱われ、整数の確認を通ってしまうため）
        if isinstance(self.n_div, bool) or not isinstance(self.n_div, int) or self.n_div < 2:
            raise ValueError(f'分割数 n_div は 2 以上の整数にしてください（{self.n_div!r}）。層の両端に質点を置くため。')

        # 初期の相対湿度が 0 より大きく 100 より小さくなければエラー
        # （0% と 100% では水分化学ポテンシャルが無限大になり、計算できないため）
        if not 0.0 < self.initial_rh < 100.0:
            raise ValueError(f'初期の相対湿度 initial_rh は 0 より大きく 100 より小さくしてください（{self.initial_rh}）。')

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        """dict から作る。

        Args:
            d: {'source', 'name', 'thickness', 'n_div', 'initial_temperature', 'initial_rh'}（すべて必ず指定する）
        """

        _check_keys(d, _MATERIAL_LAYER_KEYS, where='材料の層の入力')

        return cls(**{k: d[k] for k in _MATERIAL_LAYER_KEYS})


@dataclass(frozen=True, kw_only=True)
class AirLayerInput:
    """通気層 1 枚分の入力。

    材料を持たない（空気として扱う）。分割数は 1（よく混ざった空気の 1 つの質点）。
    層と通気層の境目の値（通気層の中の伝達率）は、ここではなく境目の入力が持つ。
    """

    # 厚さ, m
    thickness: float

    # 流量係数, -（相当開口面積 = α × 厚さ × 壁の横の長さ）
    alpha: float

    # 初期の温度, deg.C
    initial_temperature: float

    # 初期の相対湿度, %
    initial_rh: float

    @property
    def n_div(self) -> int:
        """分割数。通気層は 1 に決まっている（入力では受け取らない）。"""
        return 1

    def __post_init__(self):
        """作るときに値を確かめる。α = 0（換気のない空気層）は許す。"""

        # 厚さが 0 より大きくなければエラー（MaterialLayerInput と同じ）
        if not self.thickness > 0.0:
            raise ValueError(f'厚さ thickness は 0 より大きくしてください（{self.thickness}）。')

        # 流量係数が 0 以上でなければエラー（0 は換気のない空気層として許す）
        if not self.alpha >= 0.0:
            raise ValueError(f'流量係数 alpha は 0 以上にしてください（{self.alpha}）。')

        # 初期の相対湿度が 0 より大きく 100 より小さくなければエラー（MaterialLayerInput と同じ）
        if not 0.0 < self.initial_rh < 100.0:
            raise ValueError(f'初期の相対湿度 initial_rh は 0 より大きく 100 より小さくしてください（{self.initial_rh}）。')

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        """dict から作る。

        Args:
            d: {'air_layer': True, 'thickness', 'alpha', 'initial_temperature', 'initial_rh'}（すべて必ず指定する）
        """

        _check_keys(d, _AIR_LAYER_KEYS, where='通気層の入力')

        # 'air_layer' の値が True でなければエラー（材料の層なら、このキー自体を書かない決まり）
        if d['air_layer'] is not True:
            raise ValueError(f"通気層の入力の 'air_layer' は True にしてください（{d['air_layer']!r}）。")

        return cls(**{k: d[k] for k in _AIR_LAYER_KEYS if k != 'air_layer'})


# 層の入力：材料の層か通気層のどちらか
LayerInput = MaterialLayerInput | AirLayerInput


def layer_input_from_dict(d: dict) -> LayerInput:
    """dict から層の入力を作る。'air_layer' のキーがあれば通気層、なければ材料の層として作る。

    Args:
        d: 材料の層なら MaterialLayerInput.from_dict、通気層なら AirLayerInput.from_dict の形の dict
    """

    # 'air_layer' のキーがあれば通気層
    if 'air_layer' in d:

        # 値が True でなければエラー（材料の層なら、このキー自体を書かない決まり）
        # 先にここで確かめるのは、材料の層の dict に 'air_layer': False を書いたとき、
        # 通気層のキーの不足（'alpha' がない など）ではなく、'air_layer' の書き方の誤りとして知らせるため
        if d['air_layer'] is not True:
            raise ValueError(f"層の入力の 'air_layer' は、通気層なら True、材料の層なら書かないでください（{d['air_layer']!r}）。")

        return AirLayerInput.from_dict(d)

    # なければ材料の層
    return MaterialLayerInput.from_dict(d)


@dataclass(frozen=True, kw_only=True)
class InterfaceInput:
    """境目 1 つ分の入力（外気と最初の層、層と層、最後の層と室内）。

    層が n 枚なら、境目は n + 1 個ある。境目ごとに 1 つの値を持つ（両側の層が別々に持たない）。
    表面の伝達、層と層の接触、材料と通気層の間の伝達、塗膜・防湿層などの抵抗を、1 つのコンダクタンスにまとめて持つ。
    境目では液水は移動しない（液水のコンダクタンスを持たない。Fortran・今のコードと同じ扱い）。
    """

    # 熱コンダクタンス, W/(m2 K)
    cond_h: float

    # 湿気コンダクタンス, kg/(m2 s Pa)
    cond_m: float

    def __post_init__(self):
        """作るときに値を確かめる。値の大きさが「ふつうの範囲」かどうかは確かめない（0 以下だけを防ぐ）。"""

        # 熱コンダクタンスが 0 より大きくなければエラー（0 だと境目の両側が熱的につながらず、抵抗が 1/0 になる）
        if not self.cond_h > 0.0:
            raise ValueError(f'熱コンダクタンス cond_h は 0 より大きくしてください（{self.cond_h}）。')

        # 湿気コンダクタンスが 0 より大きくなければエラー（防湿層は 2.0e-11 などの小さい値で表す）
        if not self.cond_m > 0.0:
            raise ValueError(f'湿気コンダクタンス cond_m は 0 より大きくしてください（{self.cond_m}）。')

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        """dict から作る。

        Args:
            d: {'cond_h', 'cond_m'}（すべて必ず指定する）
        """

        _check_keys(d, _INTERFACE_KEYS, where='境目の入力')

        return cls(**{k: d[k] for k in _INTERFACE_KEYS})


@dataclass(frozen=True, kw_only=True)
class SurfaceInput:
    """壁の外表面の入力（向きと、日射・放射・風に関わる性質）。

    壁の大きさ（縦・横の長さ、換気計算用の高さ）は、ここではなく壁の入力が持つ。
    """

    # 方位（真上・真下を向いた面は TOP・BOTTOM）
    direction: Direction

    # 傾斜角, 度（0：上向きの水平、90：垂直、180：下向きの水平）
    angle: float

    # 地面の日射反射率（アルベド）, -
    albedo: float

    # 外表面の日射吸収率, -
    absorptance: float

    # 外表面の長波長放射率, -
    emissivity: float

    # 風速を求める評価高さ, m
    eva_height: float

    def __post_init__(self):
        """作るときに値を確かめる。"""

        # 方位が Direction でなければエラー（dict から作るときは from_dict で文字列から直す）
        if not isinstance(self.direction, Direction):
            raise ValueError(f'方位 direction は Direction にしてください（{self.direction!r}）。')

        # 傾斜角が方位と合っていなければエラー
        # 真上を向いた面（TOP）は 0、真下を向いた面（BOTTOM）は 180、それ以外は 0 より大きく 180 より小さい
        if self.direction == Direction.TOP:
            if self.angle != 0.0:
                raise ValueError(f'方位が top のとき、傾斜角 angle は 0 にしてください（{self.angle}）。')
        elif self.direction == Direction.BOTTOM:
            if self.angle != 180.0:
                raise ValueError(f'方位が bottom のとき、傾斜角 angle は 180 にしてください（{self.angle}）。')
        else:
            if not 0.0 < self.angle < 180.0:
                raise ValueError(f'方位が {self.direction.value} のとき、傾斜角 angle は 0 より大きく 180 より小さくしてください（{self.angle}）。'
                                 '水平な面は方位 top・bottom で表します。')

        # アルベド・日射吸収率・放射率が 0 以上 1 以下でなければエラー
        for key in ('albedo', 'absorptance', 'emissivity'):
            value = getattr(self, key)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f'{key} は 0 以上 1 以下にしてください（{value}）。')

        # 評価高さが 0 より大きくなければエラー
        if not self.eva_height > 0.0:
            raise ValueError(f'評価高さ eva_height は 0 より大きくしてください（{self.eva_height}）。')

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        """dict から作る。方位は文字列（'s'・'sw'・'w'・'nw'・'n'・'ne'・'e'・'se'・'top'・'bottom'）で受け取る。

        Args:
            d: {'direction', 'angle', 'albedo', 'absorptance', 'emissivity', 'eva_height'}（すべて必ず指定する）
        """

        _check_keys(d, _SURFACE_KEYS, where='外表面の入力')

        # 方位の文字列を Direction に直す。どれにも当たらなければエラー
        try:
            direction = Direction(d['direction'])
        except ValueError:
            raise ValueError(f"方位 direction は {[x.value for x in Direction]} のどれかにしてください（{d['direction']!r}）。") from None

        return cls(direction=direction, **{k: d[k] for k in _SURFACE_KEYS if k != 'direction'})


@dataclass(frozen=True, kw_only=True)
class WallInput:
    """壁 1 枚分の入力。

    層と境目は外気側から順に並べる。境目は層の数 + 1 個（外気と最初の層、層と層、最後の層と室内）。
    壁の面積は、使うときに 縦の長さ × 横の長さ で求める。
    """

    # 外表面
    surface: SurfaceInput

    # 層（外気側から順）
    layers: tuple[LayerInput, ...]

    # 境目（外気側から順。層の数 + 1 個）
    interfaces: tuple[InterfaceInput, ...]

    # 縦の長さ, m
    len_vertical: float

    # 横の長さ, m
    len_horizontal: float

    # 壁の下端と上端の高さの差（通気層の浮力換気に使う）, m
    height: float

    def __post_init__(self):
        """作るときに値を確かめる。"""

        # 外表面が SurfaceInput でなければエラー
        if not isinstance(self.surface, SurfaceInput):
            raise ValueError(f'外表面 surface は SurfaceInput にしてください（{type(self.surface).__name__}）。')

        # 層・境目がタプルでなければエラー（作ったあとに中身を変えられないようにするため）
        if not isinstance(self.layers, tuple) or not isinstance(self.interfaces, tuple):
            raise ValueError('層 layers と境目 interfaces はタプルにしてください。')

        # 層が 1 枚もなければエラー
        if len(self.layers) == 0:
            raise ValueError('層 layers が 1 枚もありません。')

        # 層が MaterialLayerInput・AirLayerInput のどちらでもなければエラー
        for i, layer in enumerate(self.layers):
            if not isinstance(layer, (MaterialLayerInput, AirLayerInput)):
                raise ValueError(f'層 layers の {i} 番目が層の入力ではありません（{type(layer).__name__}）。')

        # 境目が InterfaceInput でなければエラー
        for i, interface in enumerate(self.interfaces):
            if not isinstance(interface, InterfaceInput):
                raise ValueError(f'境目 interfaces の {i} 番目が境目の入力ではありません（{type(interface).__name__}）。')

        # 境目の数が「層の数 + 1」でなければエラー
        if len(self.interfaces) != len(self.layers) + 1:
            raise ValueError(f'境目 interfaces の数は、層の数 + 1（{len(self.layers) + 1}）にしてください（{len(self.interfaces)}）。')

        # いちばん外側・いちばん内側の層が通気層ならエラー（外気・室内に面する表面には材料の質点が要る）
        if isinstance(self.layers[0], AirLayerInput) or isinstance(self.layers[-1], AirLayerInput):
            raise ValueError('いちばん外側といちばん内側の層 layers は、材料の層にしてください（通気層は不可）。')

        # 通気層が 2 枚続いていればエラー（1 枚の通気層にまとめる）
        for i in range(len(self.layers) - 1):
            if isinstance(self.layers[i], AirLayerInput) and isinstance(self.layers[i + 1], AirLayerInput):
                raise ValueError(f'層 layers の {i} 番目と {i + 1} 番目が、どちらも通気層です。1 枚の通気層にまとめてください。')

        # 縦・横の長さが 0 より大きくなければエラー
        for key in ('len_vertical', 'len_horizontal'):
            value = getattr(self, key)
            if not value > 0.0:
                raise ValueError(f'{key} は 0 より大きくしてください（{value}）。')

        # 高さが 0 以上でなければエラー（水平な屋根では 0 もありうる）
        if not self.height >= 0.0:
            raise ValueError(f'高さ height は 0 以上にしてください（{self.height}）。')

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        """dict から作る。外表面・層・境目は、それぞれの from_dict の形の dict で書く（層・境目はリスト）。

        Args:
            d: {'surface', 'layers', 'interfaces', 'len_vertical', 'len_horizontal', 'height'}（すべて必ず指定する）
        """

        _check_keys(d, _WALL_KEYS, where='壁の入力')

        # 層・境目がリスト（またはタプル）でなければエラー
        for key in ('layers', 'interfaces'):
            if not isinstance(d[key], (list, tuple)):
                raise ValueError(f'壁の入力の {key} は、dict のリストで書いてください（{type(d[key]).__name__}）。')

        # 外表面・層・境目を作る。どこでエラーになったかを、メッセージの頭に付ける（番号は外気側から 0, 1, 2, …）
        surface = _from_dict_at(SurfaceInput.from_dict, d['surface'], at='surface')
        layers = tuple(_from_dict_at(layer_input_from_dict, x, at=f'layers の {i} 番目') for i, x in enumerate(d['layers']))
        interfaces = tuple(_from_dict_at(InterfaceInput.from_dict, x, at=f'interfaces の {i} 番目') for i, x in enumerate(d['interfaces']))

        # 境目の数・通気層の位置などは、ここで作るときに __post_init__ で確かめる
        return cls(surface=surface, layers=layers, interfaces=interfaces,
                   len_vertical=d['len_vertical'], len_horizontal=d['len_horizontal'], height=d['height'])
