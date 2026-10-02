"""テストファイルから要件ID⇔テストID のリンクを抽出する。

3方式（マーカー・命名規約・docstring タグ）で宣言された要件IDを収集し、
`ears_trace.parser.normalize_id` で正規化して要件ID単位のリンク辞書を返す
（R-11〜R-18）。頑健性のため、構文解析不能・読取不能なファイルはスキップし
例外を呼び出し側へ伝播させない（R-47, R-48）。

副作用は `extract_links_from_paths` のファイル読み取りのみに限定し、
`extract_links_from_source` は純粋関数として実装する。
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from ears_trace.parser import normalize_id

# ---------------------------------------------------------------------------
# 正規表現定義
# ---------------------------------------------------------------------------

# 命名規約 `test_r<NUM>_...`（R-12）。先頭の r は大文字小文字を問わない。
_NAMING_RE = re.compile(r"^test_(r\d+)_", re.IGNORECASE)

# docstring 内の `req: R-01` タグ（R-13）。正規化前の緩い表記も拾う。
_DOCSTRING_TAG_RE = re.compile(r"req:\s*([A-Za-z]{1,5}-?\d{1,4})")


def _decorator_ids(decorator: ast.expr) -> list[str]:
    """デコレータから `@pytest.mark.requirement("R-01")` の要件IDを取り出す（R-11）。

    func が属性チェーンの末尾で `requirement` 属性となっている Call のみを対象とし、
    位置引数の文字列リテラルを要件IDとして抽出する。

    Args:
        decorator: 関数に付与されたデコレータのASTノード。

    Returns:
        抽出した（正規化前の）要件ID文字列のリスト。該当しなければ空リスト。
    """
    if not isinstance(decorator, ast.Call):
        return []
    func = decorator.func
    if not isinstance(func, ast.Attribute) or func.attr != "requirement":
        return []
    ids: list[str] = []
    for arg in decorator.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            ids.append(arg.value)
    return ids


def _collect_test_ids(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """1テスト関数が宣言する要件IDを3方式から収集し正規化する（R-11〜R-14）。

    マーカー・命名規約・docstring タグの順で収集したのち、同一テスト内での
    重複を排除する（出現順を保つ）。

    Args:
        func: 対象のトップレベルテスト関数ノード。

    Returns:
        正規化済み要件IDのリスト（テスト内で重複排除・出現順）。
    """
    raw_ids: list[str] = []

    # 1. マーカー（R-11）
    for decorator in func.decorator_list:
        raw_ids.extend(_decorator_ids(decorator))

    # 2. 命名規約（R-12）
    naming_match = _NAMING_RE.match(func.name)
    if naming_match is not None:
        raw_ids.append(naming_match.group(1))

    # 3. docstring タグ（R-13）
    docstring = ast.get_docstring(func)
    if docstring is not None:
        raw_ids.extend(_DOCSTRING_TAG_RE.findall(docstring))

    # 正規化（R-14）しつつテスト内の重複を排除（出現順を保つ）。
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in raw_ids:
        req_id = normalize_id(raw)
        if req_id not in seen:
            seen.add(req_id)
            normalized.append(req_id)
    return normalized


def extract_links_from_source(source: str, *, module: str) -> dict[str, tuple[str, ...]]:
    """ソース文字列から要件ID⇔テストID のリンクを抽出する（R-11〜R-16, R-47）。

    トップレベルの `test_` 始まり関数のみを対象とし（クラス内メソッドは除外, R-16）、
    3方式で宣言された要件IDを収集・正規化する。テストIDは
    `f"{module}::{func_name}"` 形式で生成する（R-16）。要件ID単位でテストIDを
    定義順に並べたタプルとして返す。構文解析できないソースは空dictを返す（R-47）。

    Args:
        source: 解析対象の Python ソース文字列。
        module: テストIDの接頭辞となるモジュール名。

    Returns:
        `{要件ID: (テストID, ...)}` の辞書。定義順を保持し、ここでは整列しない。
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}  # 解析不能はスキップ（クラッシュしない）（R-47）

    links: dict[str, list[str]] = {}
    for node in tree.body:
        # トップレベルの関数のみ対象。クラス内メソッドは tree.body に現れない（R-16）。
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_"):
            continue  # test_ 始まりでない関数は対象外（R-46 の先取り）
        test_id = f"{module}::{node.name}"
        for req_id in _collect_test_ids(node):
            links.setdefault(req_id, []).append(test_id)

    return {req_id: tuple(test_ids) for req_id, test_ids in links.items()}


def extract_links_from_paths(paths: list[Path]) -> dict[str, tuple[str, ...]]:
    """複数ファイルのリンクを読み取り・統合して返す（R-17, R-18, R-48）。

    各ファイルを UTF-8 として読み取り、モジュール名をファイルの stem から導出する。
    読取不能（FileNotFoundError, OSError, UnicodeDecodeError）なファイルはスキップし
    処理を継続する（R-48）。全ファイルのリンクを要件ID単位で統合し（R-17）、
    テストIDは重複排除・整列して返す（R-18）。

    Args:
        paths: 走査対象のテストファイルパス一覧。

    Returns:
        `{要件ID: (テストID, ...)}` の辞書。テストIDは `sorted(set(...))` 済み。
    """
    merged: dict[str, set[str]] = {}
    for path in paths:
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # 読取不能・デコード不能はスキップ（R-48）
        file_links = extract_links_from_source(source, module=path.stem)
        for req_id, test_ids in file_links.items():
            merged.setdefault(req_id, set()).update(test_ids)

    return {req_id: tuple(sorted(test_ids)) for req_id, test_ids in merged.items()}
