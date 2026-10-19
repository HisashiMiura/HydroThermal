import os

import pandas as pd
import pytest


from modules.material_loaders import WHAMCAVITY_FILE, load_whamcavity


def test_load_whamcavity():
    """旧 Excel の19材料が、Excel と同じ順で読み込まれることを確認する。"""

    ms = load_whamcavity()

    names = pd.read_excel(WHAMCAVITY_FILE, sheet_name='material_prop')['name'].tolist()

    assert len(ms) == 19
    assert [m.name for m in ms] == names


def test_load_whamcavity_file_not_found(tmp_path):
    """ファイルがないとき、FileNotFoundError になることを確認する。"""

    with pytest.raises(FileNotFoundError):
        load_whamcavity(os.path.join(tmp_path, 'not_found.xlsx'))


def test_load_whamcavity_duplicate_name(tmp_path):
    """名前が重複しているとき、ValueError になることを確認する。

    旧 Excel の先頭の行を末尾にもう一度足した Excel を、一時フォルダ（tmp_path）に作って読む。
    """

    df = pd.read_excel(WHAMCAVITY_FILE, sheet_name='material_prop')
    df = pd.concat([df, df.iloc[[0]]])

    path = os.path.join(tmp_path, 'duplicate.xlsx')
    df.to_excel(path, sheet_name='material_prop', index=False)

    with pytest.raises(ValueError, match='重複'):
        load_whamcavity(path)
