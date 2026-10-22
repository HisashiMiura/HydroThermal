"""壁の形（時間で変わらないもの）：質点とつながり。

壁の入力（wall_input.WallInput）から作る。段階 2（docs/design/class_structure.md）で作る。
今の cell.py・wall.py の Cell と質点の配列は、置き換えが終わったら消す。

質点の置き方（設計の文書 2.3 節）：層の両端（表面・異種材料の境目）に必ず質点を置く。
層の中の質点は検査体積の中心にあり、層の端の質点は表面・境目の上にある。

つながりは、質点に「質点から検査体積の端までの抵抗」を聞いて、境目の抵抗と足す。
材料の質点と空気の質点は、同じ名前（width・heat_capacity・r_h_left・r_h_right・layer_index）で使える。
"""

from dataclasses import dataclass

from modules.materials import Material
from modules.thermo_dynamics import ROW_CP


@dataclass(frozen=True, kw_only=True)
class MaterialNode:
    """材料の質点。"""

    # 質点から検査体積の左（外気側）の端までの距離, m（層の左の端の質点は 0）
    d_left: float

    # 質点から検査体積の右（室内側）の端までの距離, m（層の右の端の質点は 0）
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
        """検査体積の幅, m（左右の端までの距離の和）"""
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

    # 相当開口面積, m2（流量係数 α × 厚さ × 壁の横の長さ）
    alpha_a: float

    # どの層の質点か（外気側から 0, 1, 2, …）
    layer_index: int

    def __post_init__(self):
        """作るときに値を確かめる。"""

        # 厚さが 0 より大きくなければエラー
        if not self.thickness > 0.0:
            raise ValueError(f'通気層の厚さ thickness は 0 より大きくしてください（{self.thickness}）。')

        # 相当開口面積が 0 以上でなければエラー（0 は換気のない空気層）
        if not self.alpha_a >= 0.0:
            raise ValueError(f'相当開口面積 alpha_a は 0 以上にしてください（{self.alpha_a}）。')

    @property
    def width(self) -> float:
        """検査体積の幅, m（通気層の厚さ）"""
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
