"""不変データモデル定義。

要件・トレースリンク・カバレッジ結果を frozen な dataclass として表現する。
集合は frozenset、系列は tuple を用い、破壊的変更を避ける（R-19〜R-25）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EarsPattern(str, Enum):
    """EARS の 5 パターン + 未分類（R-02, R-05）。

    列挙値の綴りは ears-vocabulary ステアリング規約に準拠する。
    """

    UBIQUITOUS = "UBIQUITOUS"  # THE SYSTEM SHALL ...
    EVENT = "EVENT"  # WHEN ... THE SYSTEM SHALL ...
    STATE = "STATE"  # WHILE ... THE SYSTEM SHALL ...
    UNWANTED = "UNWANTED"  # IF ... THEN THE SYSTEM SHALL ...
    OPTIONAL = "OPTIONAL"  # WHERE ... THE SYSTEM SHALL ...
    UNKNOWN = "UNKNOWN"  # いずれにも該当しない


@dataclass(frozen=True)
class Requirement:
    """要件（不変）。

    Attributes:
        id: 要件ID（明示 or 採番、一意）。R-07, R-08, R-09。
        text: 正規化済みの要件原文。R-06。
        pattern: 判定された EARS パターン。R-02, R-05。
    """

    id: str
    text: str
    pattern: EarsPattern


@dataclass(frozen=True)
class TraceLink:
    """トレースリンク（不変）。

    要件ID と、それを充足するテストID群の対応（要件側から見た 1対多）。
    R-19, R-20, R-21 に対応。

    Attributes:
        requirement_id: 対象の要件ID。R-19。
        test_ids: 充足するテストID（重複排除・整列済み）。空なら未充足。R-18, R-20。
    """

    requirement_id: str
    test_ids: tuple[str, ...]

    @property
    def is_covered(self) -> bool:
        """test_ids が非空なら covered（テスト有り）とみなす（R-21）。"""
        return len(self.test_ids) > 0


@dataclass(frozen=True)
class CoverageReport:
    """カバレッジ集計結果（不変）。

    全要件に 1件ずつ対応する TraceLink を持ち、covered/uncovered の分割と
    カバレッジ率を導出する（R-19〜R-25）。

    Attributes:
        requirements: 全要件（出現順）。R-10。
        links: 全要件に 1件ずつ対応するリンク。R-19。
        input_sha256: 入力文書の SHA-256。R-29。
        generated_at: 生成時刻（UTC, ISO 8601）。R-30。
    """

    requirements: tuple[Requirement, ...]
    links: tuple[TraceLink, ...]
    input_sha256: str
    generated_at: str = field(default="")

    @property
    def total(self) -> int:
        """要件総数（R-28）。"""
        return len(self.requirements)

    @property
    def covered_ids(self) -> frozenset[str]:
        """テストが 1件以上紐づく要件ID集合（R-21）。"""
        return frozenset(link.requirement_id for link in self.links if link.is_covered)

    @property
    def uncovered_ids(self) -> frozenset[str]:
        """全要件ID から covered を除いた集合（穴）。

        差集合で導出することで、covered ∪ uncovered = 全要件ID かつ
        covered ∩ uncovered = ∅ の分割が構造的に保証される（R-22, R-23）。
        """
        all_ids = frozenset(req.id for req in self.requirements)
        return all_ids - self.covered_ids

    @property
    def coverage_rate(self) -> float:
        """カバレッジ率 = covered 要件数 ÷ 全要件数。

        要件が 0件のときは 1.0 とみなす（R-24, R-25）。
        """
        if self.total == 0:
            return 1.0
        return len(self.covered_ids) / self.total
