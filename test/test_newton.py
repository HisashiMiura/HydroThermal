import numpy as np
import pytest
from scipy.optimize import fsolve

from modules.newton import _banded_jacobian, newton_solve, NewtonNotConverged


def _to_banded(a: np.ndarray, l: int, u: int) -> np.ndarray:
    """ふつうの形の行列を、帯の詰めた形にする（J の p 行 q 列は ab[u + p - q, q]）。"""
    n = a.shape[0]
    ab = np.zeros((l + u + 1, n))
    for p in range(n):
        for q in range(max(0, p - l), min(n, p + u + 1)):
            ab[u + p - q, q] = a[p, q]
    return ab


def _random_banded_matrix(n: int, l: int, u: int, seed: int = 0) -> np.ndarray:
    """帯の部分だけに値がある、ふつうの形の行列。"""
    rng = np.random.default_rng(seed)
    a = rng.uniform(1.0, 2.0, size=(n, n))
    for p in range(n):
        for q in range(n):
            if not (-u <= p - q <= l):
                a[p, q] = 0.0
    return a


class TestBandedJacobian:

    @pytest.mark.parametrize('l, u', [(1, 1), (3, 3)])
    def test_linear(self, l, u):
        # 1 次式 F = A x - b のヤコビ行列は A そのもの（三重対角と、熱と水分を一緒に解くときの幅 3）
        n = 10
        a = _random_banded_matrix(n, l, u)
        b = np.arange(n, dtype=float)
        x_ps = np.linspace(-1.0, 1.0, n)
        f_ps, ab = _banded_jacobian(lambda x: a @ x - b, x_ps, band=(l, u))
        np.testing.assert_allclose(ab, _to_banded(a, l, u), rtol=1e-6, atol=1e-6)
        np.testing.assert_allclose(f_ps, a @ x_ps - b)

    def test_nonlinear(self):
        # F_p = x_p^3 + x_(p-1) - 2 x_(p+1)：対角 3 x_p^2、下 1、上 -2
        def f(x):
            r = x ** 3
            r[1:] += x[:-1]
            r[:-1] -= 2.0 * x[1:]
            return r

        n = 8
        x_ps = np.linspace(0.5, 2.0, n)
        _, ab = _banded_jacobian(f, x_ps, band=(1, 1))
        expected = np.diag(3.0 * x_ps ** 2) + np.diag(np.ones(n - 1), -1) + np.diag(-2.0 * np.ones(n - 1), 1)
        np.testing.assert_allclose(ab, _to_banded(expected, 1, 1), rtol=1e-6, atol=1e-6)

    @pytest.mark.parametrize('l, u, n', [(1, 1, 33), (3, 3, 66)])
    def test_number_of_calls(self, l, u, n):
        # 残差を計算する回数は「帯の幅 + 1」（未知数の数によらない）
        calls = []
        a = _random_banded_matrix(n, l, u)

        def f(x):
            calls.append(1)
            return a @ x

        _banded_jacobian(f, np.ones(n), band=(l, u))
        assert len(calls) == l + u + 1 + 1


def _cubic(b_ps: np.ndarray):
    """非線形の式 F_p = x_p^3 + x_(p-1) - 2 x_(p+1) - b_p。"""
    def f(x):
        r = x ** 3 - b_ps
        r[1:] += x[:-1]
        r[:-1] -= 2.0 * x[1:]
        return r
    return f


class TestNewtonSolve:

    @pytest.mark.parametrize('l, u', [(1, 1), (3, 3)])
    def test_linear(self, l, u):
        # 1 次の連立方程式 A x = b：ふつうの解き方の答えと一致し、修正は 1〜2 回（三重対角と、熱と水分を一緒に解くときの幅 3）
        n = 12
        a = _random_banded_matrix(n, l, u) + np.eye(n) * 5.0
        b = np.arange(n, dtype=float)
        x_ps, m = newton_solve(lambda x: a @ x - b, np.zeros(n), band=(l, u), tol=1e-9)
        np.testing.assert_allclose(x_ps, np.linalg.solve(a, b), rtol=1e-9)
        assert 1 <= m <= 2

    def test_nonlinear(self):
        # 答え x* から b を作り、1 から始めて x* に収束する
        n = 10
        x_star = np.linspace(1.0, 2.0, n)
        b_ps = _cubic(np.zeros(n))(x_star)
        x_ps, m = newton_solve(_cubic(b_ps), np.ones(n), band=(1, 1), tol=1e-10)
        np.testing.assert_allclose(x_ps, x_star, rtol=1e-9)
        assert m > 1

    def test_already_solved(self):
        # 最初の仮の値が答えなら、修正は 0 回
        n = 10
        x_star = np.linspace(1.0, 2.0, n)
        b_ps = _cubic(np.zeros(n))(x_star)
        x_ps, m = newton_solve(_cubic(b_ps), x_star, band=(1, 1), tol=1e-10)
        assert m == 0
        np.testing.assert_allclose(x_ps, x_star)

    def test_min_iter(self):
        # 最初の仮の値の残差が許容値以下でも、min_iter = 1 なら 1 回は修正する
        n = 10
        x_star = np.linspace(1.0, 2.0, n)
        b_ps = _cubic(np.zeros(n))(x_star)
        x_ps, m = newton_solve(_cubic(b_ps), x_star + 1e-12, band=(1, 1), tol=1e-10, min_iter=1)
        assert m == 1
        np.testing.assert_allclose(x_ps, x_star, rtol=0.0, atol=1e-14)

    def test_not_converged(self):
        # 答えのない式 x_p^2 + 1 = 0 は収束しない
        with pytest.raises(NewtonNotConverged):
            newton_solve(lambda x: x ** 2 + 1.0, np.full(3, 0.7), band=(1, 1), tol=1e-10, max_iter=20)

    def test_same_as_fsolve(self):
        # 同じ非線形の式を scipy の fsolve（MINPACK）でも解き、答えが一致することで正しさを確かめる
        n = 10
        x_star = np.linspace(1.0, 2.0, n)
        f = _cubic(_cubic(np.zeros(n))(x_star))
        x_ps, _ = newton_solve(f, np.ones(n), band=(1, 1), tol=1e-10)
        x_fsolve = fsolve(f, np.ones(n), band=(1, 1), xtol=1e-12)
        np.testing.assert_allclose(x_ps, x_fsolve, rtol=1e-9)
