"""汎用のニュートン・ラフソン法（設計の文書 2.8 節）。

物理を知らない部品。未知数の並び x_p と、残差の並び F_p（p は未知数・式の番号）を扱う。
ヤコビ行列 J_pq = ∂F_p / ∂x_q は帯の形（対角の下に l 本、上に u 本）とし、
scipy.linalg.solve_banded の詰めた形 ab（J の p 行 q 列は ab[u + p - q, q]）で持つ。
"""

from collections.abc import Callable

import numpy as np

# 残差の関数：未知数の並び x_ps → 残差の並び F_ps
Residual = Callable[[np.ndarray], np.ndarray]


def banded_jacobian(f: Residual, x_ps: np.ndarray, l: int, u: int) -> tuple[np.ndarray, np.ndarray]:
    """数値微分で、帯のヤコビ行列を詰めた形で作る。

    未知数 q を h_q だけずらしたときの残差の変化から、J の q 列を求める：J の q 列 ≈ (F(x + h_q e_q) - F(x)) / h_q。
    帯の幅 w = l + u + 1 ごとに離れた未知数（q, q + w, q + 2w, …）は、影響する式が重ならないので同時にずらす。
    そのため、残差を計算する回数は w + 1 回（未知数の数によらない）。

    Args:
        f: 残差の関数
        x_ps: 未知数の並び（ここでのヤコビ行列を求める）, [p]
        l: 対角の下の帯の本数
        u: 対角の上の帯の本数

    Returns:
        x_ps での残差の並び F_ps, [p]、帯のヤコビ行列の詰めた形 ab（形は (l + u + 1, 未知数の数)）
    """

    x_ps = np.asarray(x_ps, dtype=float)
    n = len(x_ps)

    # 帯の幅
    w = l + u + 1

    # もとの残差
    f_ps = f(x_ps)

    # ずらす量, [p]（値の大きさに比例させる。値が 0 に近いときは 1 を基準にする）
    h_ps = np.sqrt(np.finfo(float).eps) * np.maximum(np.abs(x_ps), 1.0)

    ab = np.zeros((w, n))

    # 帯の幅 w ごとに離れた未知数の組を、1 組ずつまとめてずらす
    for start in range(w):

        # この組の未知数の番号（start, start + w, start + 2w, …）
        q_qs = np.arange(start, n, w)

        # この組の未知数だけをずらした残差の変化
        x_shifted_ps = x_ps.copy()
        x_shifted_ps[q_qs] += h_ps[q_qs]
        df_ps = f(x_shifted_ps) - f_ps

        # 未知数 q が影響する式は p = q - u 〜 q + l。その変化を h_q で割ったものが J の q 列
        for q in q_qs:
            for p in range(max(0, q - u), min(n, q + l + 1)):
                ab[u + p - q, q] = df_ps[p] / h_ps[q]

    return f_ps, ab
