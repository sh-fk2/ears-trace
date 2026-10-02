"""enrich モジュールの説明補足フォールバックロジックのユニットテスト。

対象要件: R-50。
WHERE --enrich が有効であり IF 外部取得が失敗/利用不可である THEN
内蔵の既定説明へフォールバックする頑健性を検証する。
report-format ステアリング規約に従い、各テストへ requirement マーカーと
docstring の `req:` タグを付与する。AAA（Arrange-Act-Assert）パターンで記述する。
"""

import pytest

from ears_trace.enrich import DEFAULT_DESCRIPTIONS, annotate
from ears_trace.models import EarsPattern


# ---------------------------------------------------------------------------
# R-50 ブランチ1: fetcher が値を返せば採用する
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-50")
def test_annotate_adopts_fetcher_value() -> None:
    """fetcher が非None文字列を返したとき、その値を採用する。

    req: R-50
    """

    # Arrange
    def fetcher(_pattern: EarsPattern) -> str | None:
        return "外部から取得した説明"

    # Act
    result = annotate(EarsPattern.EVENT, fetcher)

    # Assert
    assert result == "外部から取得した説明"


# ---------------------------------------------------------------------------
# R-50 ブランチ2: fetcher 未提供 or None なら既定説明へフォールバック
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-50")
def test_annotate_falls_back_to_default_when_no_fetcher() -> None:
    """fetcher が未提供のとき、内蔵の既定説明へフォールバックする。

    req: R-50
    """
    # Arrange
    pattern = EarsPattern.UBIQUITOUS

    # Act
    result = annotate(pattern)

    # Assert
    assert result == DEFAULT_DESCRIPTIONS[pattern]


@pytest.mark.unit
@pytest.mark.requirement("R-50")
def test_annotate_falls_back_to_default_when_fetcher_returns_none() -> None:
    """fetcher が None を返したとき、内蔵の既定説明へフォールバックする。

    req: R-50
    """
    # Arrange
    pattern = EarsPattern.STATE

    def fetcher(_pattern: EarsPattern) -> str | None:
        return None

    # Act
    result = annotate(pattern, fetcher)

    # Assert
    assert result == DEFAULT_DESCRIPTIONS[pattern]


# ---------------------------------------------------------------------------
# R-50 ブランチ3: fetcher が例外を送出しても中断せず既定へフォールバック
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-50")
def test_annotate_does_not_propagate_fetcher_exception() -> None:
    """fetcher が例外を送出しても処理を中断せず、既定説明へフォールバックする。

    req: R-50
    """
    # Arrange
    pattern = EarsPattern.UNWANTED

    def fetcher(_pattern: EarsPattern) -> str | None:
        raise RuntimeError("外部取得に失敗")

    # Act: 例外が伝播しないこと自体が検証対象
    result = annotate(pattern, fetcher)

    # Assert
    assert result == DEFAULT_DESCRIPTIONS[pattern]


# ---------------------------------------------------------------------------
# R-50: 全 EarsPattern に既定説明が存在する（フォールバック先の網羅）
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-50")
@pytest.mark.parametrize("pattern", list(EarsPattern))
def test_annotate_has_default_for_all_patterns(pattern: EarsPattern) -> None:
    """6 つの全 EarsPattern について非空の既定説明が得られる。

    req: R-50
    """
    # Act
    result = annotate(pattern)

    # Assert
    assert isinstance(result, str)
    assert result != ""


@pytest.mark.unit
@pytest.mark.requirement("R-50")
def test_annotate_falls_back_when_fetcher_returns_empty_string() -> None:
    """fetcher が空文字を返したとき、既定説明へフォールバックする。

    空文字は「値なし」とみなし、既定説明で補う（R-50 頑健性）。
    req: R-50
    """
    # Arrange
    pattern = EarsPattern.OPTIONAL

    def fetcher(_pattern: EarsPattern) -> str | None:
        return ""

    # Act
    result = annotate(pattern, fetcher)

    # Assert
    assert result == DEFAULT_DESCRIPTIONS[pattern]
