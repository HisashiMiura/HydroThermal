"""壁の状態（時間で変わるもの）：各質点の温度と水分化学ポテンシャル。

段階 3（docs/design/class_structure.md）で作る。今の wall.WallState・Wall の t_n_is・wp_n_is・state_n_is は、置き換えが終わったら消す。
水膜・木材腐朽の状態は、それぞれのモデルが持つ（設計の文書 2.6 節）。
時間を進めるときは新しい状態を作り、作ったあとは変えない。
"""

from dataclasses import dataclass

import numpy as np

from modules.state import State
from modules.thermo_dynamics import ATP


@dataclass(frozen=True, eq=False)
class WallState:
    """各質点の温度と水分化学ポテンシャル（外気側の質点から順、添え字 i）。

    配列は作るときに写しを作り、読み取り専用にする（作ったあとは中身も変えられない）。
    numpy の配列どうしの == は True/False の配列を返すので、自動の == は作らない（eq=False）。
    """

    # 温度（絶対温度）T_i, K, [i]
    t_is: np.ndarray

    # 水分化学ポテンシャル μ_i, J/kg, [i]
    mu_is: np.ndarray

    def __post_init__(self):
        """作るときに配列を確かめ、書き換えられないようにする。"""

        # 小数の配列にした写しを作る（渡された配列を、あとで外から書き換えられても影響しないように）
        t_is = np.array(self.t_is, dtype=float)
        mu_is = np.array(self.mu_is, dtype=float)

        # 1 次元でなければエラー
        if t_is.ndim != 1 or mu_is.ndim != 1:
            raise ValueError('温度 t_is と水分化学ポテンシャル mu_is は、1 次元の配列にしてください。')

        # 長さがそろっていなければエラー（どちらも質点の数）
        if len(t_is) != len(mu_is):
            raise ValueError(f'温度 t_is と水分化学ポテンシャル mu_is の長さがそろっていません（{len(t_is)}, {len(mu_is)}）。')

        # 書き換えられないようにする（読み取り専用）
        t_is.flags.writeable = False
        mu_is.flags.writeable = False

        # frozen の dataclass の項目は、ふつうの代入ができないので、この書き方で写しに入れ直す
        object.__setattr__(self, 't_is', t_is)
        object.__setattr__(self, 'mu_is', mu_is)

    def __len__(self) -> int:
        """質点の数"""
        return len(self.t_is)

    @property
    def theta_is(self) -> np.ndarray:
        """温度 θ_i, deg.C, [i]"""
        return self.t_is - ATP

    @property
    def rh_is(self) -> np.ndarray:
        """相対湿度 φ_i, %, [i]（1 点の State の rh を質点ごとに使う。式を 2 か所に書かないため）"""
        return np.array([self.state(i).rh for i in range(len(self))])

    def state(self, i: int) -> State:
        """質点 i の状態（1 点の State）。つながりの抵抗（Link.r_m など）に渡す。受け取る側は state_i と書く。"""
        return State(t=float(self.t_is[i]), mu=float(self.mu_is[i]))
