"""parser モジュールのプロパティベーステスト（PBT）。

design.md の Property P7（パーサ頑健性）・P4（要件ID一意性）・
P1（ラウンドトリップ/冪等）を Hypothesis で検証する。

parser.parse は純粋関数で例外を送出しないため、Hypothesis で大量の生成入力を
安全に流せる。ストラテジはファイル競合回避のため本ファイル内にローカル定義する
（conftest.py は編集しない）。

report-format ステアリング規約に従い、各テストへ requirement マーカーと
docstring の `req:` タグを付与し、ears-trace 自身で要件へ再リンク可能にする。
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ears_trace.models import Requirement
from ears_trace.parser import parse

# ---------------------------------------------------------------------------
# ローカルストラテジ定義
# ---------------------------------------------------------------------------

# EARS の各パターンを満たす要件本文（SHALL を含む）。分類の網羅も兼ねる。
_REQUIREMENT_BODIES: tuple[str, ...] = (
    "THE SYSTEM SHALL respond",
    "WHEN an event occurs THE SYSTEM SHALL react",
    "WHILE active THE SYSTEM SHALL poll",
    "IF an error occurs THEN THE SYSTEM SHALL abort",
    "WHERE a feature is enabled THE SYSTEM SHALL log",
)

# 明示ID候補（正規化前の緩い表記を含む）。重複・混在を意図的に許す。
_EXPLICIT_ID_PREFIXES: tuple[str, ...] = ("R-01", "R-01", "r5", "R1", "REQ-7", "R-02")

# SHALL を含まない非要件行（抽出対象外になるべき行）。
_NON_REQUIREMENT_LINES: tuple[str, ...] = (
    "これは普通の文章である。",
    "# 見出し",
    "- 箇条書きだが要件ではない",
    "",
    "SHALLOW water is dangerous",  # SHALL は単語境界を満たさず抽出されない
)


@st.composite
def requirement_line(draw: st.DrawFn) -> str:
    """要件行（SHALL を含む1行）を生成する。

    明示IDを前置するか否かをランダムに決め、重複・欠落・混在を誘発する。
    箇条書き接頭辞も確率的に付けて正規化（R-06）も揺さぶる。

    Args:
        draw: Hypothesis のドロー関数。

    Returns:
        生成された要件行テキスト（1行）。
    """
    body = draw(st.sampled_from(_REQUIREMENT_BODIES))
    has_explicit_id = draw(st.booleans())
    prefix = ""
    if has_explicit_id:
        explicit_id = draw(st.sampled_from(_EXPLICIT_ID_PREFIXES))
        prefix = f"{explicit_id}: "
    bullet = draw(st.sampled_from(("", "- ", "* ", "1. ", "## ")))
    return f"{bullet}{prefix}{body}"


@st.composite
def requirement_document(draw: st.DrawFn) -> str:
    """要件行と非要件行を混在させた複数行テキストを生成する。

    重複明示ID・採番対象・非要件ノイズを織り交ぜ、一意化（R-09）と
    出現順保持（R-10）を揺さぶる現実的な文書を作る。

    Args:
        draw: Hypothesis のドロー関数。

    Returns:
        生成された複数行の要件文書テキスト。
    """
    req_lines = draw(st.lists(requirement_line(), min_size=1, max_size=12))
    noise_lines = draw(st.lists(st.sampled_from(_NON_REQUIREMENT_LINES), max_size=6))
    all_lines = req_lines + noise_lines
    # 要件行と非要件行の順序をシャッフルして出現順の揺らぎを作る。
    draw(st.randoms()).shuffle(all_lines)
    return "\n".join(all_lines)


# ---------------------------------------------------------------------------
# 11.1 パーサ頑健性プロパティ（P7, R-45, R-46）
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.requirement("R-45")
@given(text=st.text())
def test_parse_never_raises_and_returns_tuple_for_any_text(text: str) -> None:
    """任意文字列を parse しても例外を送出せず tuple を返す（P7, R-45）。

    req: R-45
    """
    # Act: 任意文字列（制御文字・巨大入力含む）をそのまま流す
    result = parse(text)

    # Assert: 常に tuple を返し、各要素は Requirement である
    assert isinstance(result, tuple)
    assert all(isinstance(req, Requirement) for req in result)


@pytest.mark.unit
@pytest.mark.requirement("R-46")
def test_parse_returns_empty_tuple_for_empty_string() -> None:
    """空文字列では空タプルを返す（P7, R-46）。

    req: R-46
    """
    # Act / Assert
    assert parse("") == ()


@pytest.mark.unit
@pytest.mark.requirement("R-46")
@given(
    lines=st.lists(
        st.sampled_from(_NON_REQUIREMENT_LINES),
        max_size=10,
    )
)
def test_parse_returns_empty_tuple_for_non_requirement_input(lines: list[str]) -> None:
    """SHALL を含まない非要件入力では空タプルを返す（P7, R-46）。

    req: R-46
    """
    # Arrange: SHALL を単語として含まない行のみで構成する
    text = "\n".join(lines)

    # Act
    result = parse(text)

    # Assert
    assert result == ()


# ---------------------------------------------------------------------------
# 11.2 要件ID一意性プロパティ（P4, R-09）
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.requirement("R-09")
@given(text=st.text())
def test_parse_ids_are_unique_for_any_text(text: str) -> None:
    """任意文字列に対し parse 結果の要件IDに重複がない（P4, R-09）。

    req: R-09
    """
    # Act
    ids = [req.id for req in parse(text)]

    # Assert: 重複が無い（len と set のサイズが一致）
    assert len(ids) == len(set(ids))


@pytest.mark.unit
@pytest.mark.requirement("R-09")
@given(text=requirement_document())
def test_duplicate_explicit_ids_are_uniquified_in_structured_text(text: str) -> None:
    """重複明示IDを散りばめた文書でもIDが連番一意化される（P4, R-09）。

    req: R-09
    """
    # Act
    requirements = parse(text)
    ids = [req.id for req in requirements]

    # Assert: 要件が1件以上抽出され、IDに重複が無い
    assert len(requirements) >= 1
    assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# 11.3 ラウンドトリップ/冪等プロパティ（P1, R-10, R-23）
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.requirement("R-10")
@given(text=requirement_document())
def test_parse_is_idempotent_for_ids_and_order(text: str) -> None:
    """同一テキストを 2 回 parse するとIDの並び・集合が完全一致する（P1, R-10）。

    req: R-10
    """
    # Act: 同一入力を 2 回パース
    first = parse(text)
    second = parse(text)

    # Assert: IDの並び（出現順）が完全一致し、集合としても一致する
    first_ids = [req.id for req in first]
    second_ids = [req.id for req in second]
    assert first_ids == second_ids
    assert frozenset(first_ids) == frozenset(second_ids)


@pytest.mark.unit
@pytest.mark.requirement("R-23")
@given(text=requirement_document())
def test_parse_id_set_is_stable_across_reparse(text: str) -> None:
    """parse 結果のID集合が再パースを通じて安定している（P1, R-23）。

    design.md の方針に沿い、parse 結果の正規化原文を再構成して再パースしても
    要件ID集合が追加・欠落・変化なく安定することを確認する。

    req: R-23
    """
    # Arrange: 1 回目の parse 結果
    first = parse(text)
    first_ids = frozenset(req.id for req in first)

    # Act: 正規化済み原文を 1 行ずつ連結して再パース（ラウンドトリップ）
    roundtrip_text = "\n".join(req.text for req in first)
    reparsed = parse(roundtrip_text)
    reparsed_ids = frozenset(req.id for req in reparsed)

    # Assert: ID集合が一致（安定）し、件数も変わらない
    assert reparsed_ids == first_ids
    assert len(reparsed) == len(first)
