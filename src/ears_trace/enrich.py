"""EARS パターンの説明補足（enrich）ロジック。

`--enrich` 有効時に各 EARS パターンへ説明文を付与する純粋関数を提供する。
外部からの説明取得（fetcher）が失敗・利用不可でも処理を中断せず、
内蔵の既定説明へフォールバックする（R-50 頑健性）。

副作用は持たない。I/O を伴う実際の fetcher 実装は CLI 層で注入する
（python-conventions ステアリング: 副作用は cli 層に集約）。
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from ears_trace.models import EarsPattern

# EarsPattern -> 説明文 を返す取得関数の型。
# 値を返せない場合は None を返す規約とし、例外送出も許容する（呼び出し側で防御）。
AnnotationFetcher = Callable[[EarsPattern], str | None]


# 6 つの全 EARS パターンに対する内蔵の既定説明（フォールバック先）。
# ears-vocabulary ステアリング規約の列挙値に 1 対 1 対応させる。
DEFAULT_DESCRIPTIONS: dict[EarsPattern, str] = {
    EarsPattern.UBIQUITOUS: "常時成立する普遍的要件（THE SYSTEM SHALL ...）。",
    EarsPattern.EVENT: "トリガ発生に応答する要件（WHEN ... THE SYSTEM SHALL ...）。",
    EarsPattern.STATE: "特定の状態が継続する間の要件（WHILE ... THE SYSTEM SHALL ...）。",
    EarsPattern.UNWANTED: "望ましくない条件への対処要件（IF ... THEN THE SYSTEM SHALL ...）。",
    EarsPattern.OPTIONAL: "特定機能が含まれる場合の要件（WHERE ... THE SYSTEM SHALL ...）。",
    EarsPattern.UNKNOWN: "EARS のいずれのパターンにも分類できない要件。",
}

# 既定説明に未登録のパターンが来た場合の最終フォールバック（網羅保証の保険）。
_FALLBACK_DESCRIPTION = DEFAULT_DESCRIPTIONS[EarsPattern.UNKNOWN]


def _default_description(pattern: EarsPattern) -> str:
    """パターンに対応する内蔵の既定説明を返す（必ず非空文字を返す）。"""
    return DEFAULT_DESCRIPTIONS.get(pattern, _FALLBACK_DESCRIPTION)


def annotate(pattern: EarsPattern, fetcher: AnnotationFetcher | None = None) -> str:
    """EARS パターンへ説明文を付与する純粋関数。

    fetcher が非空の値を返せばそれを採用し、未提供・None・空文字・例外の
    いずれの場合も処理を中断せず内蔵の既定説明へフォールバックする（R-50）。

    Args:
        pattern: 説明を付与する対象の EARS パターン。
        fetcher: 外部説明の取得関数（任意）。None を返すか例外を送出し得る。

    Returns:
        採用された説明文、または内蔵の既定説明。常に非空文字列。
    """
    default = _default_description(pattern)
    if fetcher is None:
        return default

    try:
        fetched = fetcher(pattern)
    except Exception:
        # 外部取得の失敗で停止させない。既定説明へフォールバックする（R-50）。
        return default

    # None・空文字は「値なし」とみなし、既定説明で補う。
    if fetched:
        return fetched
    return default


def fetcher_from_mapping(mapping: dict[str, str]) -> AnnotationFetcher:
    """パターン値→説明文の写像から AnnotationFetcher を生成する（L6連携）。

    MCP（fetch サーバ）が取得した EARS パターンの注釈を、ears-vocabulary 規約の
    パターン値（例: "event", "ubiquitous"）をキーとする写像として受け取り、
    `annotate` に注入できる fetcher へ変換する。写像に無いパターンでは None を
    返し、`annotate` 側で内蔵の既定説明へフォールバックさせる（R-50）。

    Args:
        mapping: EarsPattern の値（文字列）→ 説明文 の写像。

    Returns:
        EarsPattern を受け取り説明文または None を返す fetcher。
    """

    def _fetcher(pattern: EarsPattern) -> str | None:
        return mapping.get(pattern.value)

    return _fetcher


def load_annotations(path: Path) -> dict[str, str] | None:
    """注釈 JSON ファイルを読み込み、パターン値→説明文の写像を返す（L6連携）。

    MCP（fetch）で取得・保存された注釈 JSON を実行時に読み込むための入口。
    ファイルが存在しない・読めない・壊れている・形式が不正な場合は、例外で
    停止せず None を返す（R-50 頑健性）。None は呼び出し側で「注釈なし＝内蔵の
    既定説明にフォールバック」の起点になる。

    Args:
        path: 注釈 JSON のパス。

    Returns:
        文字列キー・文字列値の写像。読み込めない場合は None。
    """
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None

    # 形式が dict でない、または値に非文字列が混じる場合は不正として None。
    if not isinstance(data, dict):
        return None
    result: dict[str, str] = {}
    for key, value in data.items():
        if isinstance(key, str) and isinstance(value, str):
            result[key] = value
    return result
