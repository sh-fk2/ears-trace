"""テスト共通の Hypothesis ストラテジ（Task 1: テスト基盤整備）。

後続タスクの PBT から再利用できるよう、以下の生成器を一箇所に集約する。

- `ears_requirement_line` / `ears_requirement_document`:
  EARS 要件テキスト（`SHALL` を含む行）と、要件行・非要件行を混在させた
  複数行文書を生成する。採番・一意化・出現順・頑健性の揺さぶりに使う。
- `requirement_id` / `test_id`:
  正規形の要件ID（`R-NN`）とテストID（`モジュール名::テスト関数名`）を生成する。
- `links_by_requirement`:
  要件ID → テストID群 の写像（`dict[str, tuple[str, ...]]`）を生成する。
  coverage/report/stub の集計系 PBT の入力に使う。

いずれも純粋関数（parser / coverage）へ安全に流せるデータのみを生成する。
各ストラテジは副作用を持たず、生成値はイミュータブル（tuple / 文字列）とする。
"""

from __future__ import annotations

from hypothesis import strategies as st

from ears_trace.models import EarsPattern, Requirement

# ---------------------------------------------------------------------------
# EARS 要件テキストのコーパス
# ---------------------------------------------------------------------------

# EARS 5 パターンそれぞれを満たす要件本文（SHALL を含む）。分類網羅も兼ねる。
EARS_BODIES: tuple[str, ...] = (
    "THE SYSTEM SHALL respond",  # Ubiquitous
    "WHEN an event occurs THE SYSTEM SHALL react",  # Event
    "WHILE active THE SYSTEM SHALL poll",  # State
    "IF an error occurs THEN THE SYSTEM SHALL abort",  # Unwanted
    "WHERE a feature is enabled THE SYSTEM SHALL log",  # Optional
)

# 正規化前の緩い明示ID表記（重複・混在を意図的に含める）。
EXPLICIT_ID_TOKENS: tuple[str, ...] = ("R-01", "R-01", "r5", "R1", "REQ-7", "R-02")

# 箇条書き・番号・見出し接頭辞（R-06 の正規化を揺さぶる）。
LINE_PREFIXES: tuple[str, ...] = ("", "- ", "* ", "+ ", "1. ", "## ")

# SHALL を含まない非要件行（抽出対象外になるべき行）。
NON_REQUIREMENT_LINES: tuple[str, ...] = (
    "これは普通の文章である。",
    "# 見出し",
    "- 箇条書きだが要件ではない",
    "",
    "SHALLOW water is dangerous",  # 単語境界を満たさず抽出されない
)


# ---------------------------------------------------------------------------
# EARS 要件テキストのストラテジ
# ---------------------------------------------------------------------------
@st.composite
def ears_requirement_line(draw: st.DrawFn) -> str:
    """要件行（`SHALL` を含む 1 行）を生成する。

    明示ID の有無・箇条書き接頭辞を確率的に付与し、採番（R-08）・一意化（R-09）・
    正規化（R-06）を揺さぶる。

    Args:
        draw: Hypothesis のドロー関数。

    Returns:
        生成された要件行テキスト（1 行）。
    """
    body = draw(st.sampled_from(EARS_BODIES))
    prefix = draw(st.sampled_from(LINE_PREFIXES))
    explicit = ""
    if draw(st.booleans()):
        explicit = f"{draw(st.sampled_from(EXPLICIT_ID_TOKENS))}: "
    return f"{prefix}{explicit}{body}"


@st.composite
def ears_requirement_document(draw: st.DrawFn) -> str:
    """要件行と非要件行を混在させた複数行の合成要件文書を生成する。

    重複明示ID・採番対象・非要件ノイズを織り交ぜ、順序もシャッフルして
    出現順保持（R-10）と一意化（R-09）を現実的に揺さぶる。少なくとも 1 件は
    要件行を含む。

    Args:
        draw: Hypothesis のドロー関数。

    Returns:
        生成された複数行の要件文書テキスト。
    """
    req_lines = draw(st.lists(ears_requirement_line(), min_size=1, max_size=12))
    noise_lines = draw(st.lists(st.sampled_from(NON_REQUIREMENT_LINES), max_size=6))
    all_lines = req_lines + noise_lines
    draw(st.randoms()).shuffle(all_lines)
    return "\n".join(all_lines)


# ---------------------------------------------------------------------------
# 要件ID / テストID のストラテジ
# ---------------------------------------------------------------------------
def requirement_id(num: int) -> str:
    """連番から正規形の要件ID（`R-NN`、2 桁ゼロ埋め）を作る補助。

    Args:
        num: 1 以上の連番。

    Returns:
        `R-01` 形式の要件ID。
    """
    return f"R-{num:02d}"


def requirement_ids(min_size: int = 0, max_size: int = 8) -> st.SearchStrategy[tuple[str, ...]]:
    """一意な正規形要件ID のタプルを生成するストラテジ。

    `R-01`..`R-NN` を連番で割り当てるため、常に重複が無い。

    Args:
        min_size: 最小件数。
        max_size: 最大件数。

    Returns:
        要件ID タプルを生成するストラテジ。
    """
    return st.integers(min_value=min_size, max_value=max_size).map(
        lambda size: tuple(requirement_id(i + 1) for i in range(size))
    )


def test_id() -> st.SearchStrategy[str]:
    """`モジュール名::テスト関数名` 形式のテストID を生成するストラテジ（R-16）。

    Returns:
        テストID を生成するストラテジ。
    """
    module = st.sampled_from(("test_a", "test_b", "pkg.test_c"))
    func = st.integers(min_value=0, max_value=9).map(lambda n: f"test_case_{n}")
    return st.builds(lambda m, f: f"{m}::{f}", module, func)


# ---------------------------------------------------------------------------
# Requirement / リンク写像のストラテジ
# ---------------------------------------------------------------------------
@st.composite
def requirements(draw: st.DrawFn, min_size: int = 0, max_size: int = 8) -> tuple[Requirement, ...]:
    """一意な要件ID を持つ `tuple[Requirement, ...]` を生成するストラテジ。

    要件ID は `R-01`..`R-NN` の正規形で一意採番する。EARS パターンは全列挙値から
    一様サンプリングし、原文は非空の短い文字列を使う（内容はプロパティに影響しない）。
    要件 0 件の境界も生成対象に含める。

    Args:
        draw: Hypothesis のドロー関数。
        min_size: 最小件数。
        max_size: 最大件数。

    Returns:
        要件タプル。
    """
    size = draw(st.integers(min_value=min_size, max_value=max_size))
    patterns = draw(st.lists(st.sampled_from(list(EarsPattern)), min_size=size, max_size=size))
    texts = draw(st.lists(st.text(min_size=1, max_size=20), min_size=size, max_size=size))
    return tuple(
        Requirement(id=requirement_id(i + 1), text=texts[i], pattern=patterns[i])
        for i in range(size)
    )


@st.composite
def links_by_requirement(
    draw: st.DrawFn, requirement_list: tuple[Requirement, ...]
) -> dict[str, tuple[str, ...]]:
    """要件ID の部分集合 → テストID群 の写像を生成するストラテジ。

    各要件を確率的に covered（テスト 1 件以上）か uncovered（未充足）に振り分け、
    covered/uncovered の混在を狙う。テストID は `モジュール名::テスト関数名` 形式。

    Args:
        draw: Hypothesis のドロー関数。
        requirement_list: 対象の要件タプル。

    Returns:
        要件ID → テストID群 の写像。uncovered な要件はキーに含めない。
    """
    links: dict[str, tuple[str, ...]] = {}
    for req in requirement_list:
        if draw(st.booleans()):
            ids = draw(st.lists(test_id(), min_size=1, max_size=3))
            links[req.id] = tuple(ids)
    return links
