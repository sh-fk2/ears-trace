"""テスト基盤（strategies モジュール + conftest フィクスチャ）の自己検証（Task 1）。

後続タスクが依存する共通ストラテジ/フィクスチャが「純粋関数へ安全に流せる
有効なデータ」を生成することを確認する。基盤そのものの健全性テストであり、
特定の要件IDではなく「全体基盤」に対応する。

- strategies が生成する要件テキストを parser.parse に流して破綻しないこと
- strategies が生成する要件/リンク写像を coverage.build_report に流せること
- conftest のフィクスチャ（固定時刻・合成要件テキスト）が利用可能であること
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ears_trace.coverage import build_report
from ears_trace.models import CoverageReport, Requirement
from ears_trace.parser import parse
from tests import strategies as strat

# ---------------------------------------------------------------------------
# strategies: EARS 要件テキスト生成器の健全性
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(line=strat.ears_requirement_line())
def test_ears_requirement_line_is_single_non_empty_line_with_shall(line: str) -> None:
    """ears_requirement_line は SHALL を含む非空 1 行を生成する。"""
    # Assert
    assert "\n" not in line
    assert line.strip() != ""
    assert "SHALL" in line.upper()


@pytest.mark.unit
@given(text=strat.ears_requirement_document())
def test_ears_requirement_document_parses_into_at_least_one_requirement(text: str) -> None:
    """生成文書は parse で 1 件以上の要件になり、IDが一意である。"""
    # Act
    requirements = parse(text)
    ids = [req.id for req in requirements]

    # Assert: 基盤が「parser に流せる有効テキスト」を生成している
    assert len(requirements) >= 1
    assert len(ids) == len(set(ids))


@pytest.mark.unit
@given(text=strat.ears_requirement_document())
def test_ears_requirement_document_never_crashes_parser(text: str) -> None:
    """生成文書で parse が例外を送出せず tuple を返す（頑健性の下支え）。"""
    # Act
    result = parse(text)

    # Assert
    assert isinstance(result, tuple)
    assert all(isinstance(req, Requirement) for req in result)


# ---------------------------------------------------------------------------
# strategies: 要件ID / テストID 生成器の健全性
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(ids=strat.requirement_ids())
def test_requirement_ids_are_normalized_and_unique(ids: tuple[str, ...]) -> None:
    """requirement_ids は `R-NN` 正規形で重複の無いタプルを生成する。"""
    # Assert
    assert len(ids) == len(set(ids))
    for rid in ids:
        assert rid.startswith("R-")
        assert len(rid.split("-")[1]) >= 2


@pytest.mark.unit
@given(tid=strat.test_id())
def test_test_id_uses_module_colon_function_format(tid: str) -> None:
    """test_id は `モジュール名::テスト関数名` 形式を生成する（R-16 準拠）。"""
    # Assert
    assert "::" in tid
    module, _, func = tid.partition("::")
    assert module != ""
    assert func.startswith("test_")


# ---------------------------------------------------------------------------
# strategies: 要件 / リンク写像生成器を集計系へ流せること
# ---------------------------------------------------------------------------


@pytest.mark.unit
@given(data=st.data())
def test_requirements_and_links_feed_build_report(data: st.DataObject) -> None:
    """requirements + links_by_requirement を build_report に流せる。"""
    # Arrange
    reqs = data.draw(strat.requirements())
    links = data.draw(strat.links_by_requirement(reqs))

    # Act
    report = build_report(reqs, links, input_text="doc")

    # Assert: 集計結果が得られ、集合分割が成立する（基盤が有効入力を生成）
    assert isinstance(report, CoverageReport)
    all_ids = frozenset(req.id for req in reqs)
    assert report.covered_ids | report.uncovered_ids == all_ids
    assert report.covered_ids & report.uncovered_ids == frozenset()


@pytest.mark.unit
@given(data=st.data())
def test_links_only_reference_existing_requirements(data: st.DataObject) -> None:
    """links_by_requirement は存在する要件IDのみをキーに持つ。"""
    # Arrange
    reqs = data.draw(strat.requirements())
    links = data.draw(strat.links_by_requirement(reqs))

    # Assert
    req_ids = {req.id for req in reqs}
    assert set(links).issubset(req_ids)


# ---------------------------------------------------------------------------
# conftest: 共有フィクスチャの健全性
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fixed_now_fixture_is_utc_aware(fixed_now: datetime) -> None:
    """fixed_now は UTC aware な datetime を返す。"""
    # Assert
    assert fixed_now.tzinfo is not None
    assert fixed_now.utcoffset() == timezone.utc.utcoffset(None)


@pytest.mark.unit
def test_fixed_now_iso_matches_fixed_now(fixed_now: datetime, fixed_now_iso: str) -> None:
    """fixed_now_iso は fixed_now の ISO 8601 文字列と一致する。"""
    # Assert
    assert fixed_now_iso == fixed_now.isoformat()


@pytest.mark.unit
def test_synthetic_requirements_text_parses_with_multiple_patterns(
    synthetic_requirements_text: str,
) -> None:
    """合成要件テキストは複数要件へパースされ、IDが一意である。"""
    # Act
    requirements = parse(synthetic_requirements_text)
    ids = [req.id for req in requirements]

    # Assert
    assert len(requirements) >= 5
    assert len(ids) == len(set(ids))
