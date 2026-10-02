"""report モジュールの HTML 生成ロジックのユニットテスト。

対象要件: R-26, R-27, R-28, R-29, R-30, R-31。
report-format ステアリング規約に従い、各テストへ requirement マーカーと
docstring の `req:` タグを付与し、自ツールで再リンク可能にする。
AAA（Arrange-Act-Assert）パターンで記述する。
"""

import html
import re
from datetime import datetime, timezone

import pytest

from ears_trace.coverage import build_report, sha256_of
from ears_trace.models import CoverageReport, EarsPattern, Requirement
from ears_trace.report import render_html

# 決定論的なテストのため固定時刻を注入する（UTC aware）。
_FIXED_NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def _sample_requirements() -> tuple[Requirement, ...]:
    """covered/uncovered が混在する要件集合を組み立てる補助。"""
    return (
        Requirement(id="R-01", text="THE SYSTEM SHALL a", pattern=EarsPattern.UBIQUITOUS),
        Requirement(id="R-02", text="WHEN x THE SYSTEM SHALL b", pattern=EarsPattern.EVENT),
        Requirement(id="R-03", text="IF y THEN THE SYSTEM SHALL c", pattern=EarsPattern.UNWANTED),
    )


def _sample_report(
    *,
    input_text: str = "THE SYSTEM SHALL foo\n",
) -> CoverageReport:
    """R-01/R-03 が covered、R-02 が uncovered のレポートを組み立てる補助。"""
    links = {"R-01": ("m::test_a",), "R-03": ("m::test_c",)}
    return build_report(_sample_requirements(), links, input_text=input_text, now=_FIXED_NOW)


# ---------------------------------------------------------------------------
# R-26: 外部依存のない自己完結の静的 HTML（インライン CSS）
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-26")
def test_render_html_is_self_contained() -> None:
    """render_html は外部リソースへ依存しない自己完結 HTML を返す。

    req: R-26
    """
    # Arrange
    report = _sample_report()

    # Act
    output = render_html(report)

    # Assert: 文書型と基本構造が揃っている
    assert output.lstrip().lower().startswith("<!doctype html>")
    assert "<html" in output.lower()
    assert "</html>" in output.lower()
    # インライン CSS を持ち、外部リソース参照（link/script/img の外部 URL）が無い
    assert "<style>" in output.lower()
    assert "<link" not in output.lower()
    assert "<script" not in output.lower()
    assert "http://" not in output
    assert "https://" not in output


# ---------------------------------------------------------------------------
# R-27: トレーサビリティ表（ID・パターン・原文・テスト・covered/gap）
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-27")
def test_render_html_contains_traceability_table() -> None:
    """全要件の ID・パターン・原文・テスト・状態が表に列挙される。

    req: R-27
    """
    # Arrange
    report = _sample_report()

    # Act
    output = render_html(report)

    # Assert: 表要素が存在する
    assert "<table" in output.lower()
    # 全要件 ID が描画される
    for req in _sample_requirements():
        assert req.id in output
    # EARS パターンが描画される
    assert EarsPattern.UBIQUITOUS.value in output
    assert EarsPattern.EVENT.value in output
    assert EarsPattern.UNWANTED.value in output
    # 要件原文が描画される
    assert "WHEN x THE SYSTEM SHALL b" in output
    # 紐づくテスト ID が描画される
    assert "m::test_a" in output
    assert "m::test_c" in output


@pytest.mark.unit
@pytest.mark.requirement("R-27")
def test_render_html_marks_covered_and_gap_status() -> None:
    """covered 要件と gap（uncovered）要件の状態が表に区別して現れる。

    req: R-27
    """
    # Arrange
    report = _sample_report()

    # Act
    output = render_html(report)

    # Assert: covered / gap の両状態ラベルが出力に含まれる
    lowered = output.lower()
    assert "covered" in lowered
    assert "gap" in lowered


# ---------------------------------------------------------------------------
# R-28: サマリ（covered/total・カバレッジ率%）
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-28")
def test_render_html_contains_summary_counts_and_rate() -> None:
    """サマリに covered/total とカバレッジ率（百分率）が含まれる。

    req: R-28
    """
    # Arrange: 3件中 2件 covered → 66.7%
    report = _sample_report()

    # Act
    output = render_html(report)

    # Assert: covered 数・total 数が描画される
    assert "2" in output
    assert "3" in output
    # 百分率が描画される（66.7% を想定、少なくとも % 記号と 66 を含む）
    assert "%" in output
    assert re.search(r"66\.?7?\s*%", output) is not None


@pytest.mark.unit
@pytest.mark.requirement("R-28")
def test_render_html_summary_full_coverage_when_empty() -> None:
    """要件 0件のときカバレッジ率 100% がサマリに現れる（R-25 連携）。

    req: R-28
    """
    # Arrange
    report = build_report((), {}, input_text="", now=_FIXED_NOW)

    # Act
    output = render_html(report)

    # Assert
    assert "100" in output
    assert "%" in output


# ---------------------------------------------------------------------------
# R-29: 入力ハッシュの埋め込み
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-29")
def test_render_html_embeds_input_sha256() -> None:
    """入力ファイル内容の SHA-256 ハッシュが HTML に埋め込まれる。

    req: R-29
    """
    # Arrange
    text = "THE SYSTEM SHALL embed-hash\n"
    report = _sample_report(input_text=text)

    # Act
    output = render_html(report)

    # Assert
    assert sha256_of(text) in output
    assert report.input_sha256 in output


# ---------------------------------------------------------------------------
# R-30: UTC 生成時刻の埋め込み
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-30")
def test_render_html_embeds_generated_at_utc() -> None:
    """生成時刻（UTC, ISO 8601）が HTML に埋め込まれる。

    req: R-30
    """
    # Arrange
    report = _sample_report()

    # Act
    output = render_html(report)

    # Assert
    assert "2026-01-02T03:04:05+00:00" in output
    assert report.generated_at in output


# ---------------------------------------------------------------------------
# R-31: HTML 特殊文字のエスケープ
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-31")
def test_render_html_escapes_requirement_text() -> None:
    """要件原文の HTML 特殊文字がエスケープされる（XSS/表崩れ防止）。

    req: R-31
    """
    # Arrange: スクリプトタグを含む悪意ある要件原文
    malicious = '<script>alert("xss")</script> THE SYSTEM SHALL x & y'
    requirements = (Requirement(id="R-01", text=malicious, pattern=EarsPattern.UBIQUITOUS),)
    report = build_report(requirements, {}, input_text="doc", now=_FIXED_NOW)

    # Act
    output = render_html(report)

    # Assert: 生の <script> は現れず、エスケープ済み表現が含まれる
    assert "<script>alert" not in output
    assert html.escape(malicious) in output


@pytest.mark.unit
@pytest.mark.requirement("R-31")
def test_render_html_escapes_test_ids() -> None:
    """テスト ID の HTML 特殊文字がエスケープされる（R-31）。

    req: R-31
    """
    # Arrange: 特殊文字を含むテスト ID
    tricky_id = 'mod::test_<b>&"x"'
    requirements = (
        Requirement(id="R-01", text="THE SYSTEM SHALL a", pattern=EarsPattern.UBIQUITOUS),
    )
    report = build_report(requirements, {"R-01": (tricky_id,)}, input_text="doc", now=_FIXED_NOW)

    # Act
    output = render_html(report)

    # Assert
    assert "test_<b>" not in output
    assert html.escape(tricky_id) in output


# ---------------------------------------------------------------------------
# 決定論性（P5 準拠）: 同一レポートからの出力は完全一致
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-26")
def test_render_html_is_deterministic() -> None:
    """同一の CoverageReport からの HTML 本文は繰り返し一致する。

    req: R-26
    """
    # Arrange
    report = _sample_report()

    # Act
    first = render_html(report)
    second = render_html(report)

    # Assert
    assert first == second
