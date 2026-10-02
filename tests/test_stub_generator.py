"""stub_generator モジュールの pytest スタブ生成ロジックのユニットテスト。

対象要件: R-32, R-33, R-34, R-35, R-36。
report-format ステアリング規約に従い、各テストへ requirement マーカーと
docstring の `req:` タグを付与し、自ツールで再リンク可能にする。
AAA（Arrange-Act-Assert）パターンで記述する。
"""

import ast
from datetime import datetime, timezone

import pytest

from ears_trace.coverage import build_report
from ears_trace.linker import extract_links_from_source
from ears_trace.models import CoverageReport, EarsPattern, Requirement
from ears_trace.stub_generator import generate_stubs

# 決定論的なテストのため固定時刻を注入する（UTC aware）。
_FIXED_NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def _sample_requirements() -> tuple[Requirement, ...]:
    """covered/uncovered が混在する要件集合を出現順で組み立てる補助。"""
    return (
        Requirement(id="R-01", text="THE SYSTEM SHALL a", pattern=EarsPattern.UBIQUITOUS),
        Requirement(id="R-02", text="WHEN x THE SYSTEM SHALL b", pattern=EarsPattern.EVENT),
        Requirement(id="R-03", text="IF y THEN THE SYSTEM SHALL c", pattern=EarsPattern.UNWANTED),
        Requirement(id="R-04", text="WHILE z THE SYSTEM SHALL d", pattern=EarsPattern.STATE),
    )


def _sample_report() -> CoverageReport:
    """R-02/R-04 が covered、R-01/R-03 が uncovered のレポートを組み立てる補助。"""
    links = {"R-02": ("m::test_b",), "R-04": ("m::test_d",)}
    return build_report(_sample_requirements(), links, input_text="doc", now=_FIXED_NOW)


# ---------------------------------------------------------------------------
# R-32 / R-34: uncovered のみを出現順でスタブ化する
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-32")
def test_generate_stubs_includes_only_uncovered() -> None:
    """covered 要件はスタブに現れず、uncovered 要件のみがスタブ化される。

    req: R-32
    """
    # Arrange
    report = _sample_report()

    # Act
    output = generate_stubs(report)

    # Assert: uncovered(R-01, R-03) は現れ、covered(R-02, R-04) は現れない
    assert '@pytest.mark.requirement("R-01")' in output
    assert '@pytest.mark.requirement("R-03")' in output
    assert '@pytest.mark.requirement("R-02")' not in output
    assert '@pytest.mark.requirement("R-04")' not in output


@pytest.mark.unit
@pytest.mark.requirement("R-34")
def test_generate_stubs_preserves_appearance_order() -> None:
    """未テスト要件は入力（requirements）の出現順でスタブ化される。

    req: R-34
    """
    # Arrange: 出現順は R-01, R-02, R-03, R-04。uncovered は R-01, R-03。
    report = _sample_report()

    # Act
    output = generate_stubs(report)

    # Assert: R-01 のスタブが R-03 のスタブより先に現れる
    index_r01 = output.index('@pytest.mark.requirement("R-01")')
    index_r03 = output.index('@pytest.mark.requirement("R-03")')
    assert index_r01 < index_r03


# ---------------------------------------------------------------------------
# R-33: マーカー＋req タグ付与で自ツールが再リンク可能
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-33")
def test_generate_stubs_adds_marker_and_req_tag() -> None:
    """各スタブにマーカーと docstring の `req:` タグが付与される。

    req: R-33
    """
    # Arrange
    report = _sample_report()

    # Act
    output = generate_stubs(report)

    # Assert: uncovered 各要件にマーカーと req タグの双方が付く
    assert '@pytest.mark.requirement("R-01")' in output
    assert "req: R-01" in output
    assert '@pytest.mark.requirement("R-03")' in output
    assert "req: R-03" in output


@pytest.mark.unit
@pytest.mark.requirement("R-33")
def test_generate_stubs_is_relinkable_by_self_tool() -> None:
    """生成物を linker で再抽出すると uncovered 要件IDが取り戻せる（自己整合）。

    req: R-33
    """
    # Arrange
    report = _sample_report()

    # Act: 生成物を自ツール（linker）で解析し直す
    output = generate_stubs(report)
    links = extract_links_from_source(output, module="test_generated_stubs")

    # Assert: 再抽出した要件ID集合が uncovered 要件IDと一致する
    assert frozenset(links.keys()) == report.uncovered_ids


# ---------------------------------------------------------------------------
# R-35: 決定論的・冪等（同一入力→同一出力）
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-35")
def test_generate_stubs_is_deterministic() -> None:
    """同一の CoverageReport からのスタブ本文は繰り返し一致する。

    req: R-35
    """
    # Arrange
    report = _sample_report()

    # Act
    first = generate_stubs(report)
    second = generate_stubs(report)

    # Assert
    assert first == second


# ---------------------------------------------------------------------------
# R-36: 未充足0件ならヘッダのみ
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-36")
def test_generate_stubs_header_only_when_all_covered() -> None:
    """全要件 covered のとき、スタブ関数本体を含まないヘッダのみを返す。

    req: R-36
    """
    # Arrange: 全要件に対しテストを紐づける
    requirements = _sample_requirements()
    links = {req.id: (f"m::test_{req.id.lower()}",) for req in requirements}
    report = build_report(requirements, links, input_text="doc", now=_FIXED_NOW)

    # Act
    output = generate_stubs(report)

    # Assert: スタブ関数（def test_）が 1 件も無い
    assert "def test_" not in output
    assert "@pytest.mark.requirement" not in output


@pytest.mark.unit
@pytest.mark.requirement("R-36")
def test_generate_stubs_header_only_when_no_requirements() -> None:
    """要件 0件のとき、スタブ関数本体を含まないヘッダのみを返す。

    req: R-36
    """
    # Arrange
    report = build_report((), {}, input_text="", now=_FIXED_NOW)

    # Act
    output = generate_stubs(report)

    # Assert: ヘッダは非空だがスタブ関数は無い
    assert output.strip() != ""
    assert "def test_" not in output


# ---------------------------------------------------------------------------
# 生成コードは構文的に valid な Python である
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-33")
def test_generate_stubs_output_is_valid_python() -> None:
    """生成されたスタブモジュールは構文的に valid な Python である。

    req: R-33
    """
    # Arrange
    report = _sample_report()

    # Act
    output = generate_stubs(report)

    # Assert: ast.parse が例外を送出しない
    ast.parse(output)


@pytest.mark.unit
@pytest.mark.requirement("R-36")
def test_generate_stubs_header_only_output_is_valid_python() -> None:
    """ヘッダのみ（未充足0件）の出力も構文的に valid な Python である。

    req: R-36
    """
    # Arrange
    report = build_report((), {}, input_text="", now=_FIXED_NOW)

    # Act
    output = generate_stubs(report)

    # Assert
    ast.parse(output)
