"""EARS パターンの説明補足（enrich）ロジック。

`--enrich` 有効時に各 EARS パターンへ説明文を付与する純粋関数を提供する。
外部からの説明取得（fetcher）が失敗・利用不可でも処理を中断せず、
内蔵の既定説明へフォールバックする（R-50 頑健性）。

副作用は持たない。I/O を伴う実際の fetcher 実装は CLI 層で注入する
（python-conventions ステアリング: 副作用は cli 層に集約）。
"""

from __future__ import annotations

from collections.abc import Callable

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
