"""要件とトレースリンクからカバレッジ集計結果を構築する（要件3: R-19〜R-25）。

本モジュールは副作用のない純粋関数のみを提供する。全要件に 1件ずつ TraceLink を
生成し（R-19）、リンク無しの要件は空集合＝未充足として表現する（R-20）。
covered/uncovered の分割やカバレッジ率の導出は `CoverageReport` の導出プロパティ側
（models.py）に委ね、ここでは重複実装しない（R-21〜R-25）。

非決定要素（現在時刻）は `now` 引数で注入可能にし、生成時刻を固定して決定論的に
テストできるようにする（R-30）。ファイルI/O 等の副作用は持たず、CLI 層へ隔離する。
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from ears_trace.models import CoverageReport, Requirement, TraceLink


def sha256_of(text: str) -> str:
    """入力文書の SHA-256 hex digest を返す（R-29）。

    Args:
        text: ハッシュ対象の文字列。

    Returns:
        UTF-8 エンコードした `text` の SHA-256 16進ダイジェスト文字列。
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _to_utc_iso8601(now: datetime | None) -> str:
    """生成時刻を UTC の ISO 8601 文字列に正規化する（R-30）。

    `now` が None なら現在の UTC 時刻を用いる。naive（tzinfo 無し）な場合は
    UTC とみなし、aware な場合は UTC に変換してから isoformat する。

    Args:
        now: 注入する生成時刻。None なら `datetime.now(timezone.utc)`。

    Returns:
        UTC タイムゾーン（`+00:00`）の ISO 8601 文字列。
    """
    moment = now if now is not None else datetime.now(timezone.utc)
    if moment.tzinfo is None:
        # naive は UTC とみなす（規約: now が naive なら UTC 扱い）。
        moment = moment.replace(tzinfo=timezone.utc)
    else:
        # aware は UTC へ変換してから文字列化する。
        moment = moment.astimezone(timezone.utc)
    return moment.isoformat()


def build_report(
    requirements: tuple[Requirement, ...],
    links_by_requirement: dict[str, tuple[str, ...]],
    *,
    input_text: str,
    now: datetime | None = None,
) -> CoverageReport:
    """要件とリンク写像から CoverageReport を構築する純粋関数（R-19〜R-30）。

    全要件に対し出現順で 1件ずつ TraceLink を生成する（R-19）。要件IDが
    `links_by_requirement` に無い場合は空の test_ids を持つ未充足リンクにする
    （R-20）。test_ids は重複排除・整列してから格納する（R-18 準拠）。
    covered/uncovered の分割とカバレッジ率は CoverageReport の導出プロパティで
    計算されるため、ここでは生成しない（R-21〜R-25）。

    Args:
        requirements: 全要件（出現順）。
        links_by_requirement: 要件ID → テストID群の写像。欠落は未充足を意味する。
        input_text: 入力文書本文。SHA-256 の計算に用いる（R-29）。
        now: 生成時刻の注入値。None なら現在の UTC 時刻（R-30）。

    Returns:
        構築した不変の `CoverageReport`。
    """
    links = tuple(
        TraceLink(
            requirement_id=req.id,
            # 重複排除・整列（R-18 準拠）。無い要件は空タプル＝未充足（R-20）。
            test_ids=tuple(sorted(set(links_by_requirement.get(req.id, ())))),
        )
        for req in requirements
    )
    return CoverageReport(
        requirements=requirements,
        links=links,
        input_sha256=sha256_of(input_text),
        generated_at=_to_utc_iso8601(now),
    )
