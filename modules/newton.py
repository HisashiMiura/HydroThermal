"""汎用のニュートン・ラフソン法（設計の文書 2.8 節）。

物理を知らない部品。未知数の並び x_p と、残差の並び F_p（p は未知数・式の番号）を扱う。
ヤコビ行列 J_pq = ∂F_p / ∂x_q は帯の形とし、帯の幅をタプル band = (l, u)（対角の下に l 本、上に u 本）で表す。
帯の幅は解く問題の形で決まるので、物理を知っている呼ぶ側が決めて渡す。
scipy.linalg.solve_banded の詰めた形 ab（J の p 行 q 列は ab[u + p - q, q]）で持つ。
"""

from collections.abc import Callable

import numpy as np
from scipy.linalg import LinAlgError, solve_banded

# 残差の関数：未知数の並び x_ps → 残差の並び F_ps
Residual = Callable[[np.ndarray], np.ndarray]


def _banded_jacobian(f: Residual, x_ps: np.ndarray, band: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """数値微分で、帯のヤコビ行列を詰めた形で作る。

    未知数 q を h_q だけずらしたときの残差の変化から、J の q 列を求める：J の q 列 ≈ (F(x + h_q e_q) - F(x)) / h_q。
    帯の幅 w = l + u + 1 ごとに離れた未知数（q, q + w, q + 2w, …）は、影響する式が重ならないので同時にずらす。
    そのため、残差を計算する回数は w + 1 回（未知数の数によらない）。

    Args:
        f: 残差の関数
        x_ps: 未知数の並び（ここでのヤコビ行列を求める）, [p]
        band: ヤコビ行列の帯の幅 (対角の下の本数 l, 上の本数 u)

    Returns:
        x_ps での残差の並び F_ps, [p]、帯のヤコビ行列の詰めた形 ab（形は (l + u + 1, 未知数の数)）
    """

    x_ps = np.asarray(x_ps, dtype=float)
    n = len(x_ps)

    # 帯の幅：対角の下の本数 l、上の本数 u
    l, u = band

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


class NewtonNotConverged(RuntimeError):
    """ニュートン法が、決めた回数のうちに収束しなかった（またはヤコビ行列が解けなかった）。"""


def newton_solve(f: Residual, x0_ps: np.ndarray, band: tuple[int, int], tol: float, max_iter: int = 20) -> tuple[np.ndarray, int]:
    """ニュートン・ラフソン法で、残差 F(x) = 0 となる x を求める。

    m 回目：残差 F と帯のヤコビ行列 J を作り、残差のいちばん大きいものが tol 以下なら終わる。
    そうでなければ、J Δx = -F を帯行列の直接法で解いて、x を x + Δx に更新する。

    Args:
        f: 残差の関数
        x0_ps: 最初の仮の値, [p]
        band: ヤコビ行列の帯の幅 (対角の下の本数 l, 上の本数 u)。熱だけなら (1, 1)
        tol: 残差の許容値（残差と同じ単位。熱なら W/m2）
        max_iter: 修正の回数の上限

    Returns:
        答え x_ps, [p]、修正した回数

    Raises:
        NewtonNotConverged: max_iter 回修正しても残差が tol 以下にならなかったとき、またはヤコビ行列が解けなかったとき
    """

    x_ps = np.array(x0_ps, dtype=float)

    for m in range(max_iter + 1):

        # 残差と帯のヤコビ行列
        f_ps, ab = _banded_jacobian(f, x_ps, band)

        # 残差のいちばん大きいものが許容値以下なら、答え（ここまでに m 回修正した）
        if np.max(np.abs(f_ps)) <= tol:
            return x_ps, m

        # 修正の回数の上限に達していたら、ここで止める（下で例外を出す）
        if m == max_iter:
            break

        # J Δx = -F を解く。ヤコビ行列が解けない（特異な）ときは、収束しなかったとして止める
        try:
            dx_ps = solve_banded(band, ab, -f_ps)
        except LinAlgError:
            raise NewtonNotConverged(f'ニュートン法の {m + 1} 回目で、ヤコビ行列が解けませんでした（特異）。') from None

        # x を更新する
        x_ps = x_ps + dx_ps

    raise NewtonNotConverged(f'ニュートン法が {max_iter} 回の修正で収束しませんでした（残差の最大 {np.max(np.abs(f_ps)):.3g}、許容値 {tol:.3g}）。')
