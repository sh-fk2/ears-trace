"""models モジュールの不変条件・導出ロジックのユニットテスト。

対象要件: R-19, R-20, R-21, R-22, R-24, R-25。
report-format ステアリング規約に従い、各テストへ requirement マーカーと
docstring の `req:` タグを付与し、自ツールで再リンク可能にする。
"""

import dataclasses

import pytest

from ears_trace.models import CoverageReport, EarsPattern, Requirement, TraceLink


@pytest.mark.unit
@pytest.mark.requirement("R-19")
def test_requirement_is_frozen() -> None:
    """Requirement は frozen で属性を再代入できない。

    req: R-19
    """
    # Arrange
    req = Requirement(id="R-01", text="THE SYSTEM SHALL foo", pattern=EarsPattern.UBIQUITOUS)

    # Act / Assert
    with pytest.raises(dataclasses.FrozenInstanceError):
        req.id = "R-02"  # type: ignore[misc]


@pytest.mark.unit
@pytest.mark.requirement("R-20")
def test_trace_link_is_frozen() -> None:
    """TraceLink は frozen で属性を再代入できない。

    req: R-20
    """
    # Arrange
    link = TraceLink(requirement_id="R-01", test_ids=("m::test_a",))

    # Act / Assert
    with pytest.raises(dataclasses.FrozenInstanceError):
        link.requirement_id = "R-02"  # type: ignore[misc]


@pytest.mark.unit
@pytest.mark.requirement("R-19")
def test_coverage_report_is_frozen() -> None:
    """CoverageReport は frozen で属性を再代入できない。

    req: R-19
    """
    # Arrange
    report = CoverageReport(
        requirements=(),
        links=(),
        input_sha256="deadbeef",
        generated_at="2026-01-01T00:00:00+00:00",
    )

    # Act / Assert
    with pytest.raises(dataclasses.FrozenInstanceError):
        report.input_sha256 = "changed"  # type: ignore[misc]


@pytest.mark.unit
@pytest.mark.requirement("R-21")
def test_is_covered_false_when_test_ids_empty() -> None:
    """test_ids が空なら is_covered は False（未充足）。

    req: R-21
    """
    # Arrange
    link = TraceLink(requirement_id="R-01", test_ids=())

    # Act / Assert
    assert link.is_covered is False


@pytest.mark.unit
@pytest.mark.requirement("R-21")
def test_is_covered_true_when_test_ids_non_empty() -> None:
    """test_ids が非空なら is_covered は True（充足）。

    req: R-21
    """
    # Arrange
    link = TraceLink(requirement_id="R-01", test_ids=("m::test_a", "m::test_b"))

    # Act / Assert
    assert link.is_covered is True


def _mixed_report() -> CoverageReport:
    """covered/uncovered が混在する具体的なレポートを組み立てる補助。"""
    requirements = (
        Requirement(id="R-01", text="THE SYSTEM SHALL a", pattern=EarsPattern.UBIQUITOUS),
        Requirement(id="R-02", text="WHEN x THE SYSTEM SHALL b", pattern=EarsPattern.EVENT),
        Requirement(id="R-03", text="IF y THEN THE SYSTEM SHALL c", pattern=EarsPattern.UNWANTED),
    )
    links = (
        TraceLink(requirement_id="R-01", test_ids=("m::test_a",)),  # covered
        TraceLink(requirement_id="R-02", test_ids=()),  # uncovered
        TraceLink(requirement_id="R-03", test_ids=("m::test_c", "m::test_d")),  # covered
    )
    return CoverageReport(
        requirements=requirements,
        links=links,
        input_sha256="hash",
        generated_at="2026-01-01T00:00:00+00:00",
    )


@pytest.mark.unit
@pytest.mark.requirement("R-21")
def test_covered_ids_are_links_with_tests() -> None:
    """covered_ids はテストが紐づく要件IDのみを含む。

    req: R-21
    """
    # Arrange
    report = _mixed_report()

    # Act
    covered = report.covered_ids

    # Assert
    assert covered == frozenset({"R-01", "R-03"})


@pytest.mark.unit
@pytest.mark.requirement("R-22")
def test_uncovered_ids_are_all_minus_covered() -> None:
    """uncovered_ids は全要件IDから covered を除いた集合（R-22）。

    req: R-22
    """
    # Arrange
    report = _mixed_report()

    # Act
    uncovered = report.uncovered_ids

    # Assert
    assert uncovered == frozenset({"R-02"})


@pytest.mark.unit
@pytest.mark.requirement("R-22")
def test_covered_and_uncovered_partition_all_ids() -> None:
    """covered ∪ uncovered == 全要件ID かつ covered ∩ uncovered == ∅（R-22, R-23）。

    req: R-22
    """
    # Arrange
    report = _mixed_report()
    all_ids = frozenset(req.id for req in report.requirements)

    # Act
    covered = report.covered_ids
    uncovered = report.uncovered_ids

    # Assert
    assert covered | uncovered == all_ids
    assert covered & uncovered == frozenset()


@pytest.mark.unit
@pytest.mark.requirement("R-24")
def test_total_counts_requirements() -> None:
    """total は要件総数を返す。

    req: R-24
    """
    # Arrange
    report = _mixed_report()

    # Act / Assert
    assert report.total == 3


@pytest.mark.unit
@pytest.mark.requirement("R-24")
def test_coverage_rate_is_covered_over_total() -> None:
    """coverage_rate は covered 要件数 ÷ 全要件数（R-24）。

    req: R-24
    """
    # Arrange
    report = _mixed_report()

    # Act / Assert
    assert report.coverage_rate == pytest.approx(2 / 3)


@pytest.mark.unit
@pytest.mark.requirement("R-25")
def test_coverage_rate_is_one_when_no_requirements() -> None:
    """要件が 0件のとき coverage_rate は 1.0 とみなす（R-25）。

    req: R-25
    """
    # Arrange
    report = CoverageReport(
        requirements=(),
        links=(),
        input_sha256="hash",
        generated_at="2026-01-01T00:00:00+00:00",
    )

    # Act / Assert
    assert report.total == 0
    assert report.coverage_rate == 1.0
