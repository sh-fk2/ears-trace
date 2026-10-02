"""coverage/report/stub_generator のプロパティベーステスト（Task 10）。

design.md のプロパティ P2/P3/P5/P6 を Hypothesis で検証する。実装モジュールは
完成済みで、ここでは副作用のない純粋関数に対して普遍的性質のみを確認する。

- P2 集合分割 (R-23): covered ∪ uncovered == 全要件ID かつ covered ∩ uncovered == ∅
- P3 単調性 (R-22, R-24): リンク追加で |uncovered| 非増加・coverage_rate 非減少
- P6 順序不変性 (R-24): 要件の並べ替えで coverage_rate が不変
- P5 決定論性・冪等性 (R-35): 同一 report からのスタブ/HTML 本文が繰り返し一致

report-format ステアリング規約に従い、各テストへ `@pytest.mark.requirement` と
docstring の `req:` タグを付与して自ツールで再リンク可能にする。
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ears_trace.coverage import build_report
from ears_trace.models import CoverageReport, Requirement
from ears_trace.report import render_html
from ears_trace.stub_generator import generate_stubs
from tests.strategies import links_by_requirement as links_strategy
from tests.strategies import requirements as requirements_strategy

# 決定論的検証のための固定時刻（UTC aware）。生成時刻を固定して時刻依存を排除する。
_FIXED_NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Hypothesis ストラテジ
# ---------------------------------------------------------------------------
# 要件タプル / リンク写像の生成器は tests/strategies.py に集約した共有ストラテジ
# （`requirements()` / `links_by_requirement()`）を再利用する（DRY, Task 1 基盤）。


def _build(
    requirements: tuple[Requirement, ...],
    links: dict[str, tuple[str, ...]],
) -> CoverageReport:
    """固定時刻でレポートを構築する補助（時刻依存を排除）。"""
    return build_report(requirements, links, input_text="doc", now=_FIXED_NOW)


# ---------------------------------------------------------------------------
# P2 集合分割プロパティ (R-23)
# ---------------------------------------------------------------------------
@pytest.mark.property
@pytest.mark.requirement("R-23")
@given(data=st.data())
def test_covered_and_uncovered_partition_all_requirement_ids(data: st.DataObject) -> None:
    """covered と uncovered は全要件ID集合をちょうど分割する（P2, R-23）。

    任意の要件集合＋リンク写像に対し、covered ∪ uncovered が全要件ID集合に一致し、
    covered ∩ uncovered が空集合になる（互いに素かつ網羅）。

    req: R-23
    """
    # Arrange
    requirements = data.draw(requirements_strategy())
    links = data.draw(links_strategy(requirements))

    # Act
    report = _build(requirements, links)
    all_ids = frozenset(req.id for req in requirements)

    # Assert: 和が全体に一致し、積が空（分割）。
    assert report.covered_ids | report.uncovered_ids == all_ids
    assert report.covered_ids & report.uncovered_ids == frozenset()


# ---------------------------------------------------------------------------
# P3 単調性プロパティ (R-22, R-24)
# ---------------------------------------------------------------------------
@pytest.mark.property
@pytest.mark.requirement("R-22")
@pytest.mark.requirement("R-24")
@given(data=st.data())
def test_adding_links_is_monotonic_for_coverage(data: st.DataObject) -> None:
    """リンク追加で |uncovered| が非増加・coverage_rate が非減少（P3, R-22, R-24）。

    ベース写像 links に未充足要件へのテストを追加した写像 links' を作ると、
    coverage_rate は非減少、uncovered 件数は非増加になる（単調性）。

    req: R-22
    req: R-24
    """
    # Arrange
    requirements = data.draw(requirements_strategy())
    base_links = data.draw(links_strategy(requirements))
    base_report = _build(requirements, base_links)

    # 現時点で未充足の要件集合から、追加でリンクする対象を選ぶ。
    uncovered = sorted(base_report.uncovered_ids)
    to_add = data.draw(st.lists(st.sampled_from(uncovered), unique=True)) if uncovered else []

    # Act: ベース写像にテストを追加した拡張写像 links' を構築する（元は不変のまま）。
    extended_links = dict(base_links)
    for req_id in to_add:
        extended_links[req_id] = ("m::test_added",)
    extended_report = _build(requirements, extended_links)

    # Assert: 単調非減少・単調非増加。
    assert extended_report.coverage_rate >= base_report.coverage_rate
    assert len(extended_report.uncovered_ids) <= len(base_report.uncovered_ids)


# ---------------------------------------------------------------------------
# P6 順序不変性プロパティ (R-24)
# ---------------------------------------------------------------------------
@pytest.mark.property
@pytest.mark.requirement("R-24")
@given(data=st.data())
def test_coverage_rate_is_invariant_under_requirement_reordering(data: st.DataObject) -> None:
    """要件を並べ替えても coverage_rate と covered/uncovered が不変（P6, R-24）。

    covered/uncovered は集合として導出されるため、要件 tuple の順序を入れ替えても
    カバレッジ率・covered 集合・uncovered 集合は変化しない。

    req: R-24
    """
    # Arrange
    requirements = data.draw(requirements_strategy())
    links = data.draw(links_strategy(requirements))
    # 同一要件集合の並べ替え（permutation）を別順序の tuple として生成する。
    permuted_requirements = tuple(data.draw(st.permutations(requirements)))

    # Act
    report = _build(requirements, links)
    permuted_report = _build(permuted_requirements, links)

    # Assert: 率と集合はいずれも順序非依存。
    assert permuted_report.coverage_rate == report.coverage_rate
    assert permuted_report.covered_ids == report.covered_ids
    assert permuted_report.uncovered_ids == report.uncovered_ids


# ---------------------------------------------------------------------------
# P5 決定論性・冪等性プロパティ (R-35)
# ---------------------------------------------------------------------------
@pytest.mark.property
@pytest.mark.requirement("R-35")
@given(data=st.data())
def test_generate_stubs_is_deterministic(data: st.DataObject) -> None:
    """同一 report から複数回生成したスタブ本文が完全一致する（P5, R-35）。

    generate_stubs は副作用のない純粋関数なので、同じ CoverageReport に対して
    何度呼んでも同一の文字列を返す（決定論的・冪等）。

    req: R-35
    """
    # Arrange
    requirements = data.draw(requirements_strategy())
    links = data.draw(links_strategy(requirements))
    report = _build(requirements, links)

    # Act
    first = generate_stubs(report)
    second = generate_stubs(report)

    # Assert
    assert first == second


@pytest.mark.property
@pytest.mark.requirement("R-35")
@given(data=st.data())
def test_render_html_is_deterministic_with_fixed_time(data: st.DataObject) -> None:
    """時刻固定の同一 report から生成した HTML 本文が繰り返し一致する（P5, R-35）。

    生成時刻を固定注入（_FIXED_NOW）すれば、入力ハッシュ・時刻も安定するため
    render_html は決定論的に同一の HTML を返す。

    req: R-35
    """
    # Arrange
    requirements = data.draw(requirements_strategy())
    links = data.draw(links_strategy(requirements))
    report = _build(requirements, links)

    # Act
    first = render_html(report)
    second = render_html(report)

    # Assert
    assert first == second
