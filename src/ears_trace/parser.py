"""要件文書のパース・EARS パターン分類・ID 採番。

純粋関数のみで構成し、ファイルI/O・標準出力・終了コードは含めない
（副作用は cli 層に隔離する）。`parse` は任意入力で例外を送出せず、
常に `tuple[Requirement, ...]` を返す（R-45, R-46）。
"""

from __future__ import annotations

import re

from ears_trace.models import EarsPattern, Requirement

# ---------------------------------------------------------------------------
# 正規表現定義
# ---------------------------------------------------------------------------

# SHALL 検出（大文字小文字を区別しない）。単語境界を要求し "SHALLOW" 等は除外する。
_SHALL_RE = re.compile(r"\bSHALL\b", re.IGNORECASE)

# インラインコード（バッククォートで囲まれた範囲）を検出する正規表現。
# 要件判定の前に除去し、`SHALL` を名詞的に引用しただけの説明文（Glossary等）を
# 要件行として誤検出しないようにする（R-01 / KI-01）。
_INLINE_CODE_RE = re.compile(r"`[^`]*`")


def _strip_inline_code(line: str) -> str:
    """行からインラインコード（バッククォート内）を除去する（R-01）。

    EARS の述語としての `SHALL` を判定するため、コード表記された `` `SHALL` ``
    のような引用を取り除いた文字列を返す。要件行かどうかの判定にのみ用い、
    抽出・表示する原文自体は変更しない。

    Args:
        line: 判定対象の1行テキスト。

    Returns:
        インラインコード範囲を除去した文字列。
    """
    return _INLINE_CODE_RE.sub(" ", line)

# EARS パターン判定。ears-vocabulary ステアリング規約の判定順序に従う。
# UNWANTED → EVENT → STATE → OPTIONAL → UBIQUITOUS。いずれも該当しなければ UNKNOWN。
_PATTERN_ORDER: tuple[tuple[EarsPattern, re.Pattern[str]], ...] = (
    (EarsPattern.UNWANTED, re.compile(r"\bIF\b.+\bTHEN\b.+\bSHALL\b", re.IGNORECASE | re.DOTALL)),
    (EarsPattern.EVENT, re.compile(r"\bWHEN\b.+\bSHALL\b", re.IGNORECASE | re.DOTALL)),
    (EarsPattern.STATE, re.compile(r"\bWHILE\b.+\bSHALL\b", re.IGNORECASE | re.DOTALL)),
    (EarsPattern.OPTIONAL, re.compile(r"\bWHERE\b.+\bSHALL\b", re.IGNORECASE | re.DOTALL)),
    (EarsPattern.UBIQUITOUS, re.compile(r"\bSHALL\b", re.IGNORECASE)),
)

# 明示ID（[A-Z]{1,5}-\d{1,4}）。正規化前の緩い表記（小文字・ハイフン無し・桁不足）も拾う。
# 例: "R-01", "r5", "R1"。行頭付近に現れる要件識別子を対象とする。
_EXPLICIT_ID_RE = re.compile(r"\b([A-Za-z]{1,5})-?(\d{1,4})\b")

# 行頭の接頭辞（箇条書き `-`・`*`・`+`、番号 `1.`、見出し `#`）と前後空白の除去用。
_PREFIX_RE = re.compile(r"^\s*(?:[-*+#]+\s*|#+\s*|\d+[.)]\s*)+")


def normalize_id(raw: str) -> str:
    """要件IDを正規形 `R-NN`（接頭辞大文字・番号2桁ゼロ埋め）に整える。

    report-format ステアリング規約の normalize_id 規約に従う
    （例: `r1` → `R-01`）。番号が 3 桁以上の場合はゼロ埋めせず桁数を保つ。

    Args:
        raw: 正規化前のID文字列（例: "r-1", "R1", "R-01"）。

    Returns:
        正規化後のID（例: "R-01"）。想定外の形式はそのまま返す。
    """
    match = re.match(r"^([A-Za-z]{1,5})-?(\d{1,4})$", raw.strip())
    if match is None:
        return raw.strip()
    prefix = match.group(1).upper()
    number = int(match.group(2))
    return f"{prefix}-{number:02d}"


def classify(text: str) -> EarsPattern:
    """1行の EARS パターンを判定する。

    判定順序は ears-vocabulary ステアリング規約に従い
    UNWANTED → EVENT → STATE → OPTIONAL → UBIQUITOUS の順に評価する。
    複合パターン（IF-THEN, WHEN 等）を単純な SHALL より先に見ることで、
    Unwanted > Event（R-03）・Optional/State > Ubiquitous（R-04）の優先度を保証する。
    いずれにも該当しなければ UNKNOWN を返す（R-05）。

    Args:
        text: 判定対象の1行テキスト。

    Returns:
        判定された EarsPattern。
    """
    for pattern, regex in _PATTERN_ORDER:
        if regex.search(text):
            return pattern
    return EarsPattern.UNKNOWN


def _normalize_line(line: str) -> str:
    """行から箇条書き・番号・見出しの接頭辞と前後空白を除去する（R-06）。

    Args:
        line: 生の1行テキスト。

    Returns:
        正規化済みの原文。
    """
    stripped = _PREFIX_RE.sub("", line)
    return stripped.strip()


def _extract_explicit_id(text: str) -> str | None:
    """正規化済み行から明示ID（[A-Z]{1,5}-\\d{1,4} 相当）を取り出す（R-07）。

    行の先頭付近に現れる最初の候補を明示IDとして採用し、正規化して返す。
    候補が見つからなければ None を返す。

    Args:
        text: 正規化済みの要件原文。

    Returns:
        正規化済みの明示ID。無ければ None。
    """
    match = _EXPLICIT_ID_RE.search(text)
    if match is None:
        return None
    return normalize_id(f"{match.group(1)}-{match.group(2)}")


def _next_auto_id(used_numbers: set[int], reserved: set[str]) -> tuple[str, int]:
    """既存IDと衝突しない採番ID（R-NN）を生成する（R-08）。

    Args:
        used_numbers: すでに採番で消費した番号の集合。
        reserved: 明示IDなどで予約済みの正規化IDの集合。

    Returns:
        (採番した正規化ID, 消費した番号) のタプル。
    """
    number = 1
    while True:
        candidate = f"R-{number:02d}"
        if number not in used_numbers and candidate not in reserved:
            return candidate, number
        number += 1


def _uniquify(base_id: str, assigned: set[str]) -> str:
    """同一IDの2件目以降へ連番接尾辞（-2, -3 …）を付けて一意化する（R-09）。

    Args:
        base_id: 採用しようとしている正規化ID。
        assigned: すでに確定した要件IDの集合。

    Returns:
        一意化された要件ID。
    """
    if base_id not in assigned:
        return base_id
    suffix = 2
    while f"{base_id}-{suffix}" in assigned:
        suffix += 1
    return f"{base_id}-{suffix}"


def parse(text: str) -> tuple[Requirement, ...]:
    """要件文書テキストから要件を抽出・分類・採番して返す。

    処理内容:
    - SHALL（大文字小文字問わず）を含む行のみ抽出する（R-01）。
    - 箇条書き・番号・見出しの接頭辞と前後空白を除去して正規化する（R-06）。
    - 明示IDがあれば採用（R-07）、無ければ衝突しない R-NN を採番（R-08）、
      重複IDは連番接尾辞で一意化する（R-09）。
    - EARS パターンを分類し（R-02, R-05）、入力の出現順で返す（R-10）。
    - 空・非要件のみの入力では空タプルを返す（R-45, R-46）。純粋関数で例外を送出しない。

    Args:
        text: 要件文書テキスト。

    Returns:
        抽出・分類・採番済みの Requirement を出現順に並べたタプル。
    """
    # 明示IDの予約集合を先に収集し、採番が明示IDと衝突しないようにする（R-08）。
    reserved_ids: set[str] = set()
    normalized_lines: list[str] = []
    for line in text.splitlines():
        # インラインコード内のみに SHALL が現れる行は要件行にしない（R-01 / KI-01）。
        if not _SHALL_RE.search(_strip_inline_code(line)):
            continue
        normalized = _normalize_line(line)
        normalized_lines.append(normalized)
        explicit = _extract_explicit_id(normalized)
        if explicit is not None:
            reserved_ids.add(explicit)

    requirements: list[Requirement] = []
    assigned_ids: set[str] = set()
    used_numbers: set[int] = set()

    for normalized in normalized_lines:
        explicit = _extract_explicit_id(normalized)
        if explicit is not None:
            base_id = explicit
        else:
            base_id, number = _next_auto_id(used_numbers, reserved_ids)
            used_numbers.add(number)
        unique_id = _uniquify(base_id, assigned_ids)
        assigned_ids.add(unique_id)
        requirements.append(
            Requirement(id=unique_id, text=normalized, pattern=classify(normalized))
        )

    return tuple(requirements)
