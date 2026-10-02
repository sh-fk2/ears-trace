"""pytest 共有フィクスチャ（Task 1: テスト基盤整備）。

後続タスクのユニット/統合/PBT から再利用できる共通フィクスチャを提供する。

- `fixed_now`: 生成時刻を固定した UTC aware `datetime`。レポート/スタブの
  決定論性（R-30, R-35）をテストする際、`build_report(..., now=fixed_now)` の
  ように注入して時刻依存を排除する。
- `fixed_now_iso`: `fixed_now` の ISO 8601 文字列表現。
- `synthetic_requirements_text`: EARS 5 パターンと明示ID・採番対象・非要件ノイズを
  含む合成要件テキスト。parser / coverage / report の決定論的な例として使う。

Hypothesis のストラテジは `tests/strategies.py` に集約する（本ファイルからは
import しない。各テストが必要に応じて明示 import する）。
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

# 決定論的検証のための固定時刻（UTC aware）。
# PBT 側の _FIXED_NOW と同一値に揃え、時刻依存を一貫して排除する。
_FIXED_NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

# EARS 5 パターン・明示ID（重複含む）・採番対象・非要件ノイズを含む合成要件テキスト。
_SYNTHETIC_REQUIREMENTS_TEXT = "\n".join(
    [
        "# 合成要件文書（テスト用）",
        "",
        "R-01: THE SYSTEM SHALL 応答を返す",
        "- WHEN イベントが発生する THE SYSTEM SHALL 反応する",
        "* WHILE 稼働中 THE SYSTEM SHALL ポーリングする",
        "1. IF エラーが発生する THEN THE SYSTEM SHALL 中断する",
        "WHERE 機能が有効 THE SYSTEM SHALL ログを出力する",
        "R-01: THE SYSTEM SHALL 重複IDを一意化する",  # 明示IDの重複（R-09）
        "明示IDを持たない THE SYSTEM SHALL 採番される",  # 採番対象（R-08）
        "これは普通の文章であり要件ではない。",  # 非要件ノイズ（R-46）
        "",
    ]
)


@pytest.fixture
def fixed_now() -> datetime:
    """決定論テスト用の固定 UTC `datetime` を返す。

    Returns:
        UTC aware な固定日時。
    """
    return _FIXED_NOW


@pytest.fixture
def fixed_now_iso() -> str:
    """固定時刻の ISO 8601 文字列表現を返す（R-30 の検証に使う）。

    Returns:
        `fixed_now` を ISO 8601 形式にした文字列。
    """
    return _FIXED_NOW.isoformat()


@pytest.fixture
def synthetic_requirements_text() -> str:
    """EARS 5 パターン・重複/採番ID・非要件行を含む合成要件テキストを返す。

    Returns:
        複数行の合成要件文書テキスト。
    """
    return _SYNTHETIC_REQUIREMENTS_TEXT
