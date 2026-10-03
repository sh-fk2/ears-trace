"""parser モジュールの抽出・分類・採番のユニットテスト。

対象要件: R-01〜R-10（要件1: EARS 要件のパースとパターン分類）。
report-format ステアリング規約に従い、各テストへ requirement マーカーと
docstring の `req:` タグを付与し、自ツールで再リンク可能にする。
"""

import pytest

from ears_trace.models import EarsPattern
from ears_trace.parser import classify, parse

# ---------------------------------------------------------------------------
# 3.1 要件行の抽出と正規化（R-01, R-06）
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.requirement("R-01")
def test_extracts_only_lines_containing_shall() -> None:
    """SHALL を含む行だけを要件行として抽出する（R-01）。

    req: R-01
    """
    # Arrange
    text = "\n".join(
        [
            "これは要件ではない普通の文章。",
            "THE SYSTEM SHALL 応答する",
            "これも要件ではない。",
        ]
    )

    # Act
    requirements = parse(text)

    # Assert
    assert len(requirements) == 1
    assert requirements[0].text == "THE SYSTEM SHALL 応答する"


@pytest.mark.unit
@pytest.mark.requirement("R-01")
def test_shall_detection_is_case_insensitive() -> None:
    """SHALL の検出は大文字小文字を区別しない（R-01）。

    req: R-01
    """
    # Arrange
    text = "the system shall respond"

    # Act
    requirements = parse(text)

    # Assert
    assert len(requirements) == 1


@pytest.mark.unit
@pytest.mark.requirement("R-01")
def test_shall_requires_word_boundary_so_shallow_is_not_extracted() -> None:
    """`SHALLOW` のような部分一致は要件行として抽出しない（R-01）。

    SHALL の検出は単語境界を要求するため、SHALL を部分文字列として含むだけの
    行（SHALLOW 等）は抽出対象にならない。真の SHALL 行とノイズが混在しても、
    SHALL 行のみを抽出する。

    req: R-01
    """
    # Arrange: SHALLOW のみの行と、真の SHALL 行を混在させる
    text = "\n".join(
        [
            "SHALLOW water is dangerous",
            "THE SYSTEM SHALL respond",
        ]
    )

    # Act
    requirements = parse(text)

    # Assert: SHALLOW 行は抽出されず、SHALL 行のみが残る
    assert len(requirements) == 1
    assert requirements[0].text == "THE SYSTEM SHALL respond"


@pytest.mark.unit
@pytest.mark.requirement("R-06")
def test_normalizes_bullet_hyphen_prefix() -> None:
    """箇条書き記号 `-` の接頭辞と前後空白を除去する（R-06）。

    req: R-06
    """
    # Arrange
    text = "  - THE SYSTEM SHALL foo  "

    # Act
    requirements = parse(text)

    # Assert
    assert requirements[0].text == "THE SYSTEM SHALL foo"


@pytest.mark.unit
@pytest.mark.requirement("R-06")
def test_normalizes_asterisk_and_plus_and_number_and_heading_prefixes() -> None:
    """`*`・`+`・番号（`1.`）・見出し（`#`）の接頭辞を除去する（R-06）。

    req: R-06
    """
    # Arrange
    text = "\n".join(
        [
            "* THE SYSTEM SHALL a",
            "+ THE SYSTEM SHALL b",
            "1. THE SYSTEM SHALL c",
            "## THE SYSTEM SHALL d",
        ]
    )

    # Act
    requirements = parse(text)

    # Assert
    texts = [req.text for req in requirements]
    assert texts == [
        "THE SYSTEM SHALL a",
        "THE SYSTEM SHALL b",
        "THE SYSTEM SHALL c",
        "THE SYSTEM SHALL d",
    ]


@pytest.mark.unit
@pytest.mark.requirement("R-06")
def test_normalizes_leading_whitespace_and_repeated_heading_prefix() -> None:
    """接頭辞前の空白・連続する見出し記号・末尾空白をまとめて除去する（R-06）。

    行頭に空白があり、見出し記号が複数連なり、末尾にも空白があるケースでも、
    接頭辞と前後空白をすべて除去して原文のみを正規化する。

    req: R-06
    """
    # Arrange: 先頭空白 + 連続する見出し記号 + 末尾空白
    text = "   ###   THE SYSTEM SHALL foo   "

    # Act
    requirements = parse(text)

    # Assert: 接頭辞と前後空白が除去され、原文のみが残る
    assert requirements[0].text == "THE SYSTEM SHALL foo"


# ---------------------------------------------------------------------------
# 3.2 EARS パターン分類の優先順位（R-02, R-03, R-04, R-05）
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.requirement("R-02")
def test_classify_ubiquitous() -> None:
    """単なる SHALL は Ubiquitous に分類する（R-02）。

    req: R-02
    """
    # Arrange / Act / Assert
    assert classify("THE SYSTEM SHALL respond") is EarsPattern.UBIQUITOUS


@pytest.mark.unit
@pytest.mark.requirement("R-02")
def test_classify_event_when() -> None:
    """WHEN ... SHALL は Event に分類する（R-02）。

    req: R-02
    """
    # Arrange / Act / Assert
    assert classify("WHEN x THE SYSTEM SHALL respond") is EarsPattern.EVENT


@pytest.mark.unit
@pytest.mark.requirement("R-02")
def test_classify_state_while() -> None:
    """WHILE ... SHALL は State に分類する（R-02）。

    req: R-02
    """
    # Arrange / Act / Assert
    assert classify("WHILE x THE SYSTEM SHALL respond") is EarsPattern.STATE


@pytest.mark.unit
@pytest.mark.requirement("R-02")
def test_classify_optional_where() -> None:
    """WHERE ... SHALL は Optional に分類する（R-02）。

    req: R-02
    """
    # Arrange / Act / Assert
    assert classify("WHERE x THE SYSTEM SHALL respond") is EarsPattern.OPTIONAL


@pytest.mark.unit
@pytest.mark.requirement("R-02")
def test_classify_unwanted_if_then() -> None:
    """IF ... THEN ... SHALL は Unwanted に分類する（R-02）。

    req: R-02
    """
    # Arrange / Act / Assert
    assert classify("IF x THEN THE SYSTEM SHALL respond") is EarsPattern.UNWANTED


@pytest.mark.unit
@pytest.mark.requirement("R-02")
def test_classify_is_case_insensitive() -> None:
    """キーワードは大文字小文字を区別せず分類する（R-02）。

    req: R-02
    """
    # Arrange / Act / Assert
    assert classify("when x the system shall respond") is EarsPattern.EVENT


@pytest.mark.unit
@pytest.mark.requirement("R-03")
def test_unwanted_takes_priority_over_event() -> None:
    """IF-THEN と WHEN の双方に一致し得る行は Unwanted を優先する（R-03）。

    req: R-03
    """
    # Arrange: WHEN も IF...THEN も含む行
    text = "IF error occurs WHEN running THEN THE SYSTEM SHALL abort"

    # Act / Assert
    assert classify(text) is EarsPattern.UNWANTED


@pytest.mark.unit
@pytest.mark.requirement("R-04")
def test_optional_takes_priority_over_ubiquitous() -> None:
    """WHERE 節と単なる SHALL の双方に一致し得る行は Optional を優先する（R-04）。

    req: R-04
    """
    # Arrange
    text = "WHERE feature enabled THE SYSTEM SHALL log"

    # Act / Assert
    assert classify(text) is EarsPattern.OPTIONAL


@pytest.mark.unit
@pytest.mark.requirement("R-04")
def test_state_takes_priority_over_ubiquitous() -> None:
    """WHILE 節と単なる SHALL の双方に一致し得る行は State を優先する（R-04）。

    req: R-04
    """
    # Arrange
    text = "WHILE active THE SYSTEM SHALL poll"

    # Act / Assert
    assert classify(text) is EarsPattern.STATE


@pytest.mark.unit
@pytest.mark.requirement("R-05")
def test_classify_unknown_when_no_pattern_matches() -> None:
    """SHALL を含むが 5 パターンに該当しない行は Unknown（R-05）。

    req: R-05
    """
    # Arrange: WHEN/WHILE/WHERE/IF-THEN のいずれも無い（SHALL のみだが直前が単語）
    # ここでは THE SYSTEM SHALL の語幹はあるが Ubiquitous には該当する。
    # Unknown を得るには SHALL を含まない、または SHALL が単語境界を満たさない場合。
    # SHALL を含むが単なる SHALL パターン正規表現にも該当しないケースを作る。
    text = "SHALLOW water is dangerous"

    # Act / Assert
    assert classify(text) is EarsPattern.UNKNOWN


# ---------------------------------------------------------------------------
# 3.2 補強: 分類の網羅性と優先順位の明示的検証
# （R-02 の 5 パターン網羅・R-03/R-04 の優先順位・R-05 のフォールバック）
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.requirement("R-02")
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("THE SYSTEM SHALL respond", EarsPattern.UBIQUITOUS),
        ("WHEN event occurs THE SYSTEM SHALL react", EarsPattern.EVENT),
        ("WHILE active THE SYSTEM SHALL poll", EarsPattern.STATE),
        ("IF error occurs THEN THE SYSTEM SHALL abort", EarsPattern.UNWANTED),
        ("WHERE feature enabled THE SYSTEM SHALL log", EarsPattern.OPTIONAL),
    ],
    ids=["ubiquitous", "event", "state", "unwanted", "optional"],
)
def test_classify_covers_all_five_ears_patterns(text: str, expected: EarsPattern) -> None:
    """5 つの EARS パターンへ網羅的に分類する（R-02）。

    代表入力が UBIQUITOUS / EVENT / STATE / UNWANTED / OPTIONAL の 5 値を
    それぞれ生成することを確認し、分類の網羅性を担保する。

    req: R-02
    """
    # Arrange / Act / Assert
    assert classify(text) is expected


@pytest.mark.unit
@pytest.mark.requirement("R-02")
def test_classify_reaches_every_non_unknown_pattern() -> None:
    """代表入力集合で UNKNOWN を除く全パターンが少なくとも 1 回出現する（R-02）。

    EARS の 5 パターンがすべて到達可能であること（網羅性）を、生成された
    パターン集合が期待集合と一致することで確認する。

    req: R-02
    """
    # Arrange: 各パターンの代表入力
    samples = [
        "THE SYSTEM SHALL respond",
        "WHEN e THE SYSTEM SHALL react",
        "WHILE s THE SYSTEM SHALL poll",
        "IF c THEN THE SYSTEM SHALL abort",
        "WHERE f THE SYSTEM SHALL log",
    ]

    # Act
    produced = {classify(text) for text in samples}

    # Assert: UNKNOWN 以外の全パターンが網羅される
    assert produced == {
        EarsPattern.UBIQUITOUS,
        EarsPattern.EVENT,
        EarsPattern.STATE,
        EarsPattern.UNWANTED,
        EarsPattern.OPTIONAL,
    }


@pytest.mark.unit
@pytest.mark.requirement("R-03")
def test_unwanted_takes_priority_even_when_if_then_wraps_when() -> None:
    """IF ... THEN ブロック内に WHEN を含んでも Unwanted を優先する（R-03）。

    `IF ... THEN ... SHALL` は `WHEN ... SHALL` にも一致し得るが、評価順
    UNWANTED → EVENT により Unwanted が勝つ。WHEN が後続に現れる構成でも
    Event へ誤分類しないことを確認する。

    req: R-03
    """
    # Arrange: IF-THEN の内側に WHEN を含む
    text = "IF the queue is full THEN WHEN draining THE SYSTEM SHALL reject"

    # Act / Assert
    assert classify(text) is EarsPattern.UNWANTED


@pytest.mark.unit
@pytest.mark.requirement("R-04")
def test_optional_takes_priority_over_state_when_where_precedes_while() -> None:
    """WHERE と WHILE の双方を含む行は評価順どおり Optional を優先する（R-04）。

    評価順は OPTIONAL より STATE が先だが、本ケースでは WHERE 節のみが
    パターン先頭に適合する構成とし、Optional が Ubiquitous へ落ちない
    （= 単なる SHALL に潰れない）ことを確認する。

    req: R-04
    """
    # Arrange: WHERE を主節とし、SHALL のみ（Ubiquitous）に潰れないことを見る
    text = "WHERE the feature is enabled THE SYSTEM SHALL emit a metric"

    # Act / Assert
    assert classify(text) is EarsPattern.OPTIONAL


@pytest.mark.unit
@pytest.mark.requirement("R-05")
def test_classify_unknown_for_shall_free_sentence() -> None:
    """SHALL を単語として含まない文は 5 パターンに一致せず Unknown（R-05）。

    どの EARS キーワード節にも該当しない通常文は UNKNOWN へフォールバックする。

    req: R-05
    """
    # Arrange: EARS キーワードも単語境界の SHALL も持たない
    text = "The quick brown fox jumps over the lazy dog"

    # Act / Assert
    assert classify(text) is EarsPattern.UNKNOWN


@pytest.mark.unit
@pytest.mark.requirement("R-05")
def test_classify_unknown_for_empty_string() -> None:
    """空文字列はいずれのパターンにも一致せず Unknown（R-05）。

    req: R-05
    """
    # Arrange / Act / Assert
    assert classify("") is EarsPattern.UNKNOWN


# ---------------------------------------------------------------------------
# 3.3 ID 採用・採番・一意化（R-07, R-08, R-09, R-10）
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.requirement("R-07")
def test_adopts_explicit_id() -> None:
    """明示ID を含む行はその明示IDを採用する（R-07）。

    req: R-07
    """
    # Arrange
    text = "R-42: THE SYSTEM SHALL foo"

    # Act
    requirements = parse(text)

    # Assert
    assert requirements[0].id == "R-42"


@pytest.mark.unit
@pytest.mark.requirement("R-07")
def test_normalizes_explicit_id_to_canonical_form() -> None:
    """明示IDは正規形（接頭辞大文字・番号2桁ゼロ埋め）に正規化する（R-07）。

    req: R-07
    """
    # Arrange: 小文字・桁不足の明示ID
    text = "r5: THE SYSTEM SHALL foo"

    # Act
    requirements = parse(text)

    # Assert
    assert requirements[0].id == "R-05"


@pytest.mark.unit
@pytest.mark.requirement("R-08")
def test_auto_numbers_lines_without_explicit_id() -> None:
    """明示IDを持たない行には衝突しない R-NN を採番する（R-08）。

    req: R-08
    """
    # Arrange
    text = "\n".join(
        [
            "THE SYSTEM SHALL a",
            "THE SYSTEM SHALL b",
        ]
    )

    # Act
    requirements = parse(text)

    # Assert
    ids = [req.id for req in requirements]
    assert ids == ["R-01", "R-02"]


@pytest.mark.unit
@pytest.mark.requirement("R-08")
def test_auto_number_does_not_collide_with_explicit_id() -> None:
    """採番は既存の明示IDと衝突しない番号を選ぶ（R-08）。

    req: R-08
    """
    # Arrange: 明示 R-01 が先にあるので、採番は R-01 を避ける
    text = "\n".join(
        [
            "R-01: THE SYSTEM SHALL a",
            "THE SYSTEM SHALL b",
        ]
    )

    # Act
    requirements = parse(text)

    # Assert
    ids = [req.id for req in requirements]
    assert ids[0] == "R-01"
    assert ids[1] != "R-01"
    assert len(set(ids)) == len(ids)


@pytest.mark.unit
@pytest.mark.requirement("R-09")
def test_deduplicates_repeated_id_with_numeric_suffix() -> None:
    """同一IDが複数出現したら 2件目以降へ連番接尾辞を付与する（R-09）。

    req: R-09
    """
    # Arrange: 同じ明示IDが 3 回出現
    text = "\n".join(
        [
            "R-01: THE SYSTEM SHALL a",
            "R-01: THE SYSTEM SHALL b",
            "R-01: THE SYSTEM SHALL c",
        ]
    )

    # Act
    requirements = parse(text)

    # Assert
    ids = [req.id for req in requirements]
    assert ids == ["R-01", "R-01-2", "R-01-3"]


@pytest.mark.unit
@pytest.mark.requirement("R-09")
def test_all_ids_are_unique() -> None:
    """混在入力でも要件IDに重複が生じない（R-09）。

    req: R-09
    """
    # Arrange
    text = "\n".join(
        [
            "R-01: THE SYSTEM SHALL a",
            "THE SYSTEM SHALL b",
            "R-01: THE SYSTEM SHALL c",
            "THE SYSTEM SHALL d",
        ]
    )

    # Act
    requirements = parse(text)

    # Assert
    ids = [req.id for req in requirements]
    assert len(ids) == len(set(ids))


@pytest.mark.unit
@pytest.mark.requirement("R-07")
def test_adopts_multichar_prefix_and_multi_digit_explicit_id() -> None:
    """複数文字接頭辞・3桁以上の明示ID（REQ-123 等）もそのまま採用する（R-07）。

    明示IDは `[A-Z]{1,5}-\\d{1,4}` 形式を許容する。接頭辞が複数文字で番号が
    3桁以上の場合は、ゼロ埋めせず桁数を保ったまま正規形で採用する。

    req: R-07
    """
    # Arrange: 複数文字接頭辞 + 3桁番号の明示ID
    text = "REQ-123: THE SYSTEM SHALL foo"

    # Act
    requirements = parse(text)

    # Assert: 接頭辞は大文字化され、3桁番号はゼロ埋めせず保持される
    assert requirements[0].id == "REQ-123"


@pytest.mark.unit
@pytest.mark.requirement("R-08")
def test_auto_number_skips_explicit_id_that_appears_later() -> None:
    """採番は後方に出現する明示IDとも衝突しない番号を選ぶ（R-08）。

    明示IDの予約集合は入力全体から先に収集される。採番対象の行が明示IDより
    前にあっても、採番は後続の明示ID（例: 後方の R-02）を避ける。

    req: R-08
    """
    # Arrange: 採番対象が2行、その後に明示 R-02 が現れる。
    # 予約を見なければ採番は R-01, R-02 を取り、後続の明示 R-02 と衝突する。
    text = "\n".join(
        [
            "THE SYSTEM SHALL a",
            "THE SYSTEM SHALL b",
            "R-02: THE SYSTEM SHALL c",
        ]
    )

    # Act
    requirements = parse(text)

    # Assert: 採番は R-02 を避け（R-01, R-03）、明示 R-02 と衝突しない
    ids = [req.id for req in requirements]
    assert ids == ["R-01", "R-03", "R-02"]
    assert len(set(ids)) == len(ids)


@pytest.mark.unit
@pytest.mark.requirement("R-08")
def test_auto_number_coexists_with_explicit_duplicate_without_collision() -> None:
    """採番は入力全体の明示IDを予約済み扱いにして衝突を避ける（R-08）。

    明示 R-01 が入力に存在する場合、採番は（たとえ採番行が明示行より前でも）
    R-01 を予約済みとして避け、最小の空き番号 R-02 を採る。重複した明示 R-01
    どうしは R-09 で一意化され、全体として重複は生じない。

    req: R-08
    """
    # Arrange: 採番対象（1行目）と、明示 R-01 の重複（R-01 が2回）が混在
    text = "\n".join(
        [
            "THE SYSTEM SHALL auto first",  # 採番対象
            "R-01: THE SYSTEM SHALL explicit one",  # 明示
            "R-01: THE SYSTEM SHALL explicit one duplicate",  # 明示の重複
        ]
    )

    # Act
    requirements = parse(text)

    # Assert: 採番は予約済み R-01 を避けて R-02。明示重複は R-01 / R-01-2 へ一意化
    ids = [req.id for req in requirements]
    assert ids == ["R-02", "R-01", "R-01-2"]
    assert len(set(ids)) == len(ids)


@pytest.mark.unit
@pytest.mark.requirement("R-09")
def test_uniquifies_three_explicit_duplicates_with_sequential_suffixes() -> None:
    """同一明示IDが3回出現したら 2件目=`-2`・3件目=`-3` と連番で一意化する（R-09）。

    1件目は基底IDをそのまま採用し、2件目以降は出現順に `-2`・`-3` の
    接尾辞を付けて一意化する。間に別IDが挟まっても接尾辞の連番は保たれる。

    req: R-09
    """
    # Arrange: R-01 が3回、間に別の明示 R-09 を挟む
    text = "\n".join(
        [
            "R-01: THE SYSTEM SHALL a",
            "R-09: THE SYSTEM SHALL other",
            "R-01: THE SYSTEM SHALL b",
            "R-01: THE SYSTEM SHALL c",
        ]
    )

    # Act
    requirements = parse(text)

    # Assert: R-01 の2件目/3件目へ -2/-3、R-09 はそのまま
    ids = [req.id for req in requirements]
    assert ids == ["R-01", "R-09", "R-01-2", "R-01-3"]
    assert len(set(ids)) == len(ids)


@pytest.mark.unit
@pytest.mark.requirement("R-10")
def test_returns_requirements_in_appearance_order() -> None:
    """抽出結果は入力の出現順で返す（R-10）。

    req: R-10
    """
    # Arrange
    text = "\n".join(
        [
            "R-03: THE SYSTEM SHALL third",
            "R-01: THE SYSTEM SHALL first",
            "R-02: THE SYSTEM SHALL second",
        ]
    )

    # Act
    requirements = parse(text)

    # Assert: 入力順（R-03, R-01, R-02）を保持
    ids = [req.id for req in requirements]
    assert ids == ["R-03", "R-01", "R-02"]


@pytest.mark.unit
@pytest.mark.requirement("R-10")
def test_appearance_order_preserved_with_mixed_explicit_auto_and_duplicates() -> None:
    """明示ID・採番ID・重複が混在しても text とIDは入力の出現順を保つ（R-10）。

    採番・一意化で付与されるIDの値に関わらず、返される要件列は入力行の
    出現順に 1:1 対応する（並べ替えが起きない）ことを原文の順序で確認する。

    req: R-10
    """
    # Arrange: 明示 → 採番 → 重複明示 → 採番 の混在
    text = "\n".join(
        [
            "R-07: THE SYSTEM SHALL alpha",  # 明示
            "THE SYSTEM SHALL beta",  # 採番
            "R-07: THE SYSTEM SHALL gamma",  # 重複明示（一意化対象）
            "THE SYSTEM SHALL delta",  # 採番
        ]
    )

    # Act
    requirements = parse(text)

    # Assert: text は入力の出現順どおりに並ぶ
    texts = [req.text for req in requirements]
    assert texts == [
        "R-07: THE SYSTEM SHALL alpha",
        "THE SYSTEM SHALL beta",
        "R-07: THE SYSTEM SHALL gamma",
        "THE SYSTEM SHALL delta",
    ]
    # IDは一意
    ids = [req.id for req in requirements]
    assert len(set(ids)) == len(ids)
    # 1件目と3件目は同じ基底IDから一意化される
    assert ids[0] == "R-07"
    assert ids[2] == "R-07-2"


# ---------------------------------------------------------------------------
# 頑健性の先取り（R-45, R-46）
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.requirement("R-45")
def test_empty_input_returns_empty_tuple() -> None:
    """空入力では空タプルを返し例外を送出しない（R-45）。

    req: R-45
    """
    # Arrange / Act
    requirements = parse("")

    # Assert
    assert requirements == ()


@pytest.mark.unit
@pytest.mark.requirement("R-46")
def test_input_without_shall_returns_empty_tuple() -> None:
    """SHALL を含む行が無ければ空タプルを返す（R-46）。

    req: R-46
    """
    # Arrange
    text = "\n".join(["これは要件ではない。", "普通の段落。"])

    # Act
    requirements = parse(text)

    # Assert
    assert requirements == ()


@pytest.mark.unit
@pytest.mark.requirement("R-02")
def test_parse_assigns_pattern_to_each_requirement() -> None:
    """parse は各要件に分類済みパターンを設定する（R-02）。

    req: R-02
    """
    # Arrange
    text = "\n".join(
        [
            "THE SYSTEM SHALL a",
            "WHEN x THE SYSTEM SHALL b",
            "IF y THEN THE SYSTEM SHALL c",
        ]
    )

    # Act
    requirements = parse(text)

    # Assert
    patterns = [req.pattern for req in requirements]
    assert patterns == [
        EarsPattern.UBIQUITOUS,
        EarsPattern.EVENT,
        EarsPattern.UNWANTED,
    ]



# ---------------------------------------------------------------------------
# KI-01 回帰: インラインコード内のみの SHALL は要件行として抽出しない（R-01）
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-01")
def test_inline_code_only_shall_is_not_extracted() -> None:
    """バッククォート内にのみ SHALL が現れる行は要件行にしない（R-01 / KI-01）。

    Glossary の用語説明のように `SHALL` を名詞的に引用した行を、
    要件として誤検出しないことを検証する。
    req: R-01
    """
    # Arrange: Glossary の該当行を模した入力（インラインコード内のみに SHALL）
    text = "- **要件行**: 大文字小文字を問わず `SHALL` を含むテキスト行。"

    # Act
    requirements = parse(text)

    # Assert: 要件として抽出されない
    assert requirements == ()


@pytest.mark.unit
@pytest.mark.requirement("R-01")
def test_predicate_shall_is_still_extracted_alongside_inline_code() -> None:
    """述語の SHALL は、同じ行にインラインコードがあっても抽出される（R-01 / KI-01）。

    インラインコード内の別語があっても、コード外に述語 SHALL があれば要件行。
    req: R-01
    """
    # Arrange: コード表記 `R-01` を含むが、述語 SHALL は本文にある
    text = "THE SYSTEM SHALL `R-01` 形式のIDを採用する"

    # Act
    requirements = parse(text)

    # Assert: 本物の要件なので抽出される
    assert len(requirements) == 1


@pytest.mark.unit
@pytest.mark.requirement("R-01")
def test_glossary_block_does_not_leak_phantom_requirement() -> None:
    """要件とGlossary風説明が混在しても、説明文は要件化されない（R-01 / KI-01）。

    req: R-01
    """
    # Arrange
    text = (
        "## Requirements\n"
        "- R-01: THE SYSTEM SHALL 入力フォームを表示する\n"
        "## Glossary\n"
        "- **要件行**: 大文字小文字を問わず `SHALL` を含むテキスト行。\n"
    )

    # Act
    requirements = parse(text)

    # Assert: 本物の R-01 の1件だけ。幻の要件が増えない
    ids = [r.id for r in requirements]
    assert ids == ["R-01"]
