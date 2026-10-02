"""coverage モジュールのレポート構築ロジックのユニットテスト。

対象要件: R-19, R-20, R-21, R-22, R-24, R-25, R-29, R-30。
report-format ステアリング規約に従い、各テストへ requirement マーカーと
docstring の `req:` タグを付与し、自ツールで再リンク可能にする。
AAA（Arrange-Act-Assert）パターンで記述する。
"""

import hashlib
from datetime import datetime, timedelta, timezone

import pytest

from ears_trace.coverage import build_report, sha256_of
from ears_trace.models import EarsPattern, Requirement

# 決定論的なテストのため固定時刻を注入する（UTC aware）。
_FIXED_NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def _sample_requirements() -> tuple[Requirement, ...]:
    """covered/uncovered が混在する要件集合を組み立てる補助。"""
    return (
        Requirement(id="R-01", text="THE SYSTEM SHALL a", pattern=EarsPattern.UBIQUITOUS),
        Requirement(id="R-02", text="WHEN x THE SYSTEM SHALL b", pattern=EarsPattern.EVENT),
        Requirement(id="R-03", text="IF y THEN THE SYSTEM SHALL c", pattern=EarsPattern.UNWANTED),
    )


# ---------------------------------------------------------------------------
# R-19: 全要件に 1件ずつ TraceLink を生成する
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-19")
def test_build_report_creates_one_link_per_requirement() -> None:
    """build_report は全要件に 1件ずつ、出現順で TraceLink を生成する。

    req: R-19
    """
    # Arrange
    requirements = _sample_requirements()
    links_by_requirement = {"R-01": ("m::test_a",)}

    # Act
    report = build_report(requirements, links_by_requirement, input_text="doc", now=_FIXED_NOW)

    # Assert
    assert len(report.links) == len(requirements)
    assert tuple(link.requirement_id for link in report.links) == ("R-01", "R-02", "R-03")


# ---------------------------------------------------------------------------
# R-20: リンク無しの要件は空集合＝未充足
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-20")
def test_requirement_without_links_is_uncovered() -> None:
    """links_by_requirement に無い要件は空の test_ids で未充足となる。

    req: R-20
    """
    # Arrange
    requirements = _sample_requirements()
    links_by_requirement = {"R-01": ("m::test_a",)}

    # Act
    report = build_report(requirements, links_by_requirement, input_text="doc", now=_FIXED_NOW)
    link_r02 = next(link for link in report.links if link.requirement_id == "R-02")

    # Assert
    assert link_r02.test_ids == ()
    assert link_r02.is_covered is False


# ---------------------------------------------------------------------------
# R-21 / R-22: covered / uncovered の算出
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-21")
def test_covered_ids_from_mixed_input() -> None:
    """covered_ids はテストが紐づく要件IDのみを含む（R-21）。

    req: R-21
    """
    # Arrange
    requirements = _sample_requirements()
    links_by_requirement = {"R-01": ("m::test_a",), "R-03": ("m::test_c",)}

    # Act
    report = build_report(requirements, links_by_requirement, input_text="doc", now=_FIXED_NOW)

    # Assert
    assert report.covered_ids == frozenset({"R-01", "R-03"})


@pytest.mark.unit
@pytest.mark.requirement("R-22")
def test_uncovered_ids_from_mixed_input() -> None:
    """uncovered_ids は全要件IDから covered を除いた集合（R-22）。

    req: R-22
    """
    # Arrange
    requirements = _sample_requirements()
    links_by_requirement = {"R-01": ("m::test_a",), "R-03": ("m::test_c",)}

    # Act
    report = build_report(requirements, links_by_requirement, input_text="doc", now=_FIXED_NOW)

    # Assert
    assert report.uncovered_ids == frozenset({"R-02"})


# ---------------------------------------------------------------------------
# R-24: カバレッジ率
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-24")
def test_coverage_rate_from_mixed_input() -> None:
    """coverage_rate は covered 要件数 ÷ 全要件数（R-24）。

    req: R-24
    """
    # Arrange
    requirements = _sample_requirements()
    links_by_requirement = {"R-01": ("m::test_a",), "R-03": ("m::test_c",)}

    # Act
    report = build_report(requirements, links_by_requirement, input_text="doc", now=_FIXED_NOW)

    # Assert
    assert report.coverage_rate == pytest.approx(2 / 3)


# ---------------------------------------------------------------------------
# R-25: 要件 0件のときカバレッジ率は 1.0
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-25")
def test_coverage_rate_is_one_when_no_requirements() -> None:
    """要件が 0件のとき coverage_rate は 1.0、links も空（R-25）。

    req: R-25
    """
    # Arrange / Act
    report = build_report((), {}, input_text="", now=_FIXED_NOW)

    # Assert
    assert report.total == 0
    assert report.links == ()
    assert report.coverage_rate == 1.0


# ---------------------------------------------------------------------------
# R-18 準拠: test_ids は重複排除・整列済み
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-19")
def test_build_report_dedupes_and_sorts_test_ids() -> None:
    """生成される TraceLink の test_ids は重複排除・整列済み（R-18 準拠）。

    req: R-19
    """
    # Arrange
    requirements = (
        Requirement(id="R-01", text="THE SYSTEM SHALL a", pattern=EarsPattern.UBIQUITOUS),
    )
    # 重複あり・非整列の入力
    links_by_requirement = {"R-01": ("m::test_b", "m::test_a", "m::test_b")}

    # Act
    report = build_report(requirements, links_by_requirement, input_text="doc", now=_FIXED_NOW)

    # Assert
    assert report.links[0].test_ids == ("m::test_a", "m::test_b")


# ---------------------------------------------------------------------------
# R-29: input_sha256
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-29")
def test_sha256_of_matches_hashlib() -> None:
    """sha256_of は hashlib の SHA-256 hex digest と一致する（R-29）。

    req: R-29
    """
    # Arrange
    text = "THE SYSTEM SHALL foo\n"
    expected = hashlib.sha256(text.encode("utf-8")).hexdigest()

    # Act
    actual = sha256_of(text)

    # Assert
    assert actual == expected


@pytest.mark.unit
@pytest.mark.requirement("R-29")
def test_build_report_sets_input_sha256() -> None:
    """build_report は input_sha256 に入力文書のハッシュを設定する（R-29）。

    req: R-29
    """
    # Arrange
    text = "THE SYSTEM SHALL foo\n"
    expected = hashlib.sha256(text.encode("utf-8")).hexdigest()

    # Act
    report = build_report(_sample_requirements(), {}, input_text=text, now=_FIXED_NOW)

    # Assert
    assert report.input_sha256 == expected
    assert report.input_sha256 == sha256_of(text)


# ---------------------------------------------------------------------------
# R-30: generated_at（UTC, ISO 8601, 注入可能）
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-30")
def test_generated_at_from_injected_aware_datetime() -> None:
    """aware な now 注入で決定論的な UTC ISO 8601 文字列になる（R-30）。

    req: R-30
    """
    # Arrange / Act
    report = build_report((), {}, input_text="", now=_FIXED_NOW)

    # Assert
    assert report.generated_at == "2026-01-02T03:04:05+00:00"


@pytest.mark.unit
@pytest.mark.requirement("R-30")
def test_generated_at_treats_naive_as_utc() -> None:
    """naive な now は UTC とみなして ISO 8601 文字列化する（R-30）。

    req: R-30
    """
    # Arrange
    naive = datetime(2026, 1, 2, 3, 4, 5)  # tzinfo なし

    # Act
    report = build_report((), {}, input_text="", now=naive)

    # Assert
    assert report.generated_at == "2026-01-02T03:04:05+00:00"


@pytest.mark.unit
@pytest.mark.requirement("R-30")
def test_generated_at_converts_non_utc_aware_to_utc() -> None:
    """UTC 以外の aware な now は UTC に変換してから文字列化する（R-30）。

    req: R-30
    """
    # Arrange: +09:00 の 12:04:05 は UTC では 03:04:05
    jst = timezone(timedelta(hours=9))
    aware_jst = datetime(2026, 1, 2, 12, 4, 5, tzinfo=jst)

    # Act
    report = build_report((), {}, input_text="", now=aware_jst)

    # Assert
    assert report.generated_at == "2026-01-02T03:04:05+00:00"
