"""未充足（uncovered）要件に対応する pytest スタブを生成する（要件5: R-32〜R-36）。

本モジュールは副作用のない純粋関数のみを提供する。ファイル書き出しは CLI 層へ
隔離し、ここではスタブモジュールの文字列生成のみを担う。

生成するスタブの要件:
- uncovered（未テスト）要件に対応する pytest 雛形のみを生成する（R-32）。
- 各スタブに `@pytest.mark.requirement("R-NN")` マーカーと docstring の
  `req: R-NN` タグを付与し、生成物を自ツール（linker）で再リンク可能にする（R-33）。
- uncovered 要件を入力（requirements）の出現順でスタブ化する（R-34）。
- 同一の CoverageReport からは常に同一の文字列を返す（決定論的・冪等）（R-35）。
- uncovered が 0件ならヘッダのみを返す（R-36）。

テスト関数は `test_r<NN>_...` の命名規約とマーカー・docstring タグの 3方式で
要件IDを宣言し、ears-trace 自身が再抽出できる形式にする（report-format /
ears-vocabulary ステアリング規約に準拠）。要件原文は pytest ファイル内の
docstring/コメントに入れるため HTML エスケープは不要。
"""

from __future__ import annotations

from ears_trace.models import CoverageReport, Requirement

# スタブモジュールのヘッダ（R-36: uncovered 0件でもこの部分のみを返す）。
# 生成物自体が pytest で収集可能かつ linker で再リンク可能になるよう import を含む。
_HEADER = '''\
"""ears-trace が自動生成した未充足要件向け pytest スタブ。

本ファイルは `generate_stubs` が uncovered（未テスト）要件に対して生成した
雛形である。各テストは実装前のプレースホルダであり、`pytest.skip` で明示的に
スキップされる。中身を実装したうえで skip を外すこと。
"""

import pytest
'''


def _marker_id(requirement_id: str) -> str:
    """命名規約 `test_r<NN>_...` に用いる要件IDの数値部を取り出す。

    `R-01` 形式の要件IDから接頭辞・ハイフンを除いた識別子部分（例: `01`）を返す。
    命名規約・マーカー・docstring タグの 3方式いずれでも再リンクできるよう、
    linker の命名規約正規表現 `test_(r\\d+)_` に合致する関数名を作るために使う。

    Args:
        requirement_id: `R-01` などの正規化済み要件ID。

    Returns:
        関数名に埋め込む数値部文字列（ハイフン無し）。
    """
    # `R-01` -> `01`。想定外の形式でも末尾の数値列があればそれを採用する。
    _, _, tail = requirement_id.partition("-")
    return tail or requirement_id


def _stub_for(requirement: Requirement) -> str:
    """1つの uncovered 要件に対する pytest スタブ関数のソースを返す（R-33, R-34）。

    マーカー `@pytest.mark.requirement("R-NN")`・命名規約 `test_r<NN>_...`・
    docstring の `req: R-NN` タグの 3方式すべてで要件IDを宣言し、自ツールで
    確実に再リンクできるようにする（R-33）。本体は `pytest.skip` のプレースホルダ。

    Args:
        requirement: スタブ化対象の未充足要件。

    Returns:
        スタブ関数 1件分のソース文字列（前後に空行を含む）。
    """
    req_id = requirement.id
    func_name = f"test_r{_marker_id(req_id)}_stub"
    # 要件原文は pytest ファイル内の docstring に入れるためエスケープ不要。
    # ただしソースを壊さないよう三重引用符の衝突だけ無害化する。
    safe_text = requirement.text.replace('"""', '\\"\\"\\"')
    return (
        "\n\n"
        f'@pytest.mark.requirement("{req_id}")\n'
        f"def {func_name}() -> None:\n"
        f'    """{req_id} の未充足要件に対する自動生成スタブ。\n'
        "\n"
        f"    要件原文: {safe_text}\n"
        f"    req: {req_id}\n"
        '    """\n'
        f'    pytest.skip("未実装の自動生成スタブ（{req_id}）。実装後に skip を外すこと。")\n'
    )


def generate_stubs(report: CoverageReport) -> str:
    """CoverageReport から未充足要件向け pytest スタブを生成する純粋関数（R-32〜R-36）。

    uncovered（未テスト）要件のみを対象とし（R-32）、入力 `report.requirements` の
    出現順でスタブ化する（R-34）。各スタブにはマーカーと `req:` タグを付与し、
    自ツールで再リンク可能にする（R-33）。同一入力に対し常に同一の文字列を返す
    （決定論的・冪等）（R-35）。uncovered が 0件ならヘッダのみを返す（R-36）。

    Args:
        report: スタブ生成対象の不変なカバレッジ集計結果。

    Returns:
        pytest スタブモジュールのソース文字列。uncovered 0件ならヘッダのみ。
    """
    uncovered_ids = report.uncovered_ids
    # 出現順（requirements の並び順）を保ちつつ uncovered のみを抽出する（R-32, R-34）。
    stubs = [_stub_for(req) for req in report.requirements if req.id in uncovered_ids]
    # uncovered 0件ならヘッダのみ（末尾を 1 行で終える）（R-36）。
    if not stubs:
        return _HEADER
    return _HEADER + "".join(stubs)
