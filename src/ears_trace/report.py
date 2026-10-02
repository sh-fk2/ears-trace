"""カバレッジ集計結果から自己完結 HTML レポートを生成する（要件4: R-26〜R-31）。

本モジュールは副作用のない純粋関数のみを提供する。ファイル書き出しは CLI 層へ
隔離し、ここでは HTML 文字列の生成のみを担う。

生成する HTML の要件:
- 外部リソースに依存しない自己完結の静的 HTML（インライン CSS）。R-26。
- 全要件の ID・EARS パターン・原文・紐づくテスト・covered/gap 状態を列挙した
  トレーサビリティ表。R-27。
- covered 要件数 / 全要件数とカバレッジ率（百分率）のサマリ。R-28。
- 入力文書の SHA-256 ハッシュ（R-29）と UTC ISO 8601 の生成時刻（R-30）の埋め込み。
- 入力由来の文字列（要件原文・テスト ID）は必ず HTML エスケープする（R-31）。

入力は信頼しない（外部データ）。要件原文やテスト ID は `html.escape` で
エスケープしてから描画し、XSS や表崩れを防ぐ（R-31）。
"""

from __future__ import annotations

import html

from ears_trace.models import CoverageReport, TraceLink

# インライン CSS（R-26: 外部リソースへ依存しない自己完結スタイル）。
_INLINE_CSS = """\
    body { font-family: -apple-system, Segoe UI, Roboto, sans-serif;
           margin: 2rem; color: #1a1a1a; }
    h1 { font-size: 1.5rem; }
    .summary { margin: 1rem 0; padding: 0.75rem 1rem;
               background: #f3f4f6; border-radius: 6px; }
    .summary strong { font-size: 1.1rem; }
    table { border-collapse: collapse; width: 100%; margin-top: 1rem; }
    th, td { border: 1px solid #d1d5db; padding: 0.5rem 0.75rem;
             text-align: left; vertical-align: top; }
    th { background: #e5e7eb; }
    td.text { max-width: 40rem; }
    .status-covered { color: #047857; font-weight: 600; }
    .status-gap { color: #b91c1c; font-weight: 600; }
    .meta { margin-top: 1.5rem; font-size: 0.85rem; color: #4b5563; }
    .meta code { word-break: break-all; }
"""


def _status_cell(link: TraceLink) -> str:
    """covered/gap 状態を表すセル HTML を返す（R-27）。"""
    if link.is_covered:
        return '<td class="status-covered">covered</td>'
    return '<td class="status-gap">gap</td>'


def _tests_cell(link: TraceLink) -> str:
    """紐づくテスト ID をエスケープして列挙するセル HTML を返す（R-27, R-31）。

    テスト ID は入力由来の文字列のため、必ずエスケープする（R-31）。
    """
    if not link.test_ids:
        return "<td></td>"
    # 各テスト ID をエスケープし、<br> で区切って縦に並べる。
    escaped = "<br>".join(html.escape(test_id) for test_id in link.test_ids)
    return f"<td>{escaped}</td>"


def _row_html(report: CoverageReport, link: TraceLink) -> str:
    """1要件分のトレーサビリティ表の行 HTML を返す（R-27, R-31）。"""
    # requirement_id に対応する要件を引く（build_report は 1対1 で生成する）。
    requirement = next(req for req in report.requirements if req.id == link.requirement_id)
    # 要件 ID・パターン名・原文は入力由来のためエスケープする（R-31）。
    req_id = html.escape(requirement.id)
    pattern = html.escape(requirement.pattern.value)
    text = html.escape(requirement.text)
    return (
        "<tr>"
        f"<td>{req_id}</td>"
        f"<td>{pattern}</td>"
        f'<td class="text">{text}</td>'
        f"{_tests_cell(link)}"
        f"{_status_cell(link)}"
        "</tr>"
    )


def _summary_html(report: CoverageReport) -> str:
    """covered/total とカバレッジ率（百分率）のサマリ HTML を返す（R-28）。"""
    covered = len(report.covered_ids)
    total = report.total
    # カバレッジ率を百分率（小数第1位）で表示する。
    percent = f"{report.coverage_rate * 100:.1f}"
    return f'<div class="summary"><strong>Coverage: {covered} / {total} ({percent}%)</strong></div>'


def _table_html(report: CoverageReport) -> str:
    """全要件を列挙したトレーサビリティ表 HTML を返す（R-27）。"""
    header = (
        "<thead><tr>"
        "<th>ID</th><th>Pattern</th><th>Requirement</th>"
        "<th>Tests</th><th>Status</th>"
        "</tr></thead>"
    )
    rows = "".join(_row_html(report, link) for link in report.links)
    return f"<table>{header}<tbody>{rows}</tbody></table>"


def _meta_html(report: CoverageReport) -> str:
    """入力ハッシュ（R-29）と生成時刻（R-30）のメタ情報 HTML を返す。

    ハッシュと時刻はツールが生成する値だが、改変に備えて念のため
    エスケープしてから描画する。
    """
    sha = html.escape(report.input_sha256)
    generated_at = html.escape(report.generated_at)
    return (
        '<div class="meta">'
        f"<div>Input SHA-256: <code>{sha}</code></div>"
        f"<div>Generated at (UTC): <code>{generated_at}</code></div>"
        "</div>"
    )


def render_html(report: CoverageReport) -> str:
    """CoverageReport から自己完結 HTML を生成する純粋関数（R-26〜R-31）。

    外部リソースに依存しないインライン CSS 付きの静的 HTML を返す（R-26）。
    トレーサビリティ表（R-27）・サマリ（R-28）・入力ハッシュ（R-29）・
    UTC 生成時刻（R-30）を埋め込み、入力由来の文字列はすべてエスケープする（R-31）。
    同一入力に対して常に同一の出力を返す（決定論的）。

    Args:
        report: レンダリング対象の不変なカバレッジ集計結果。

    Returns:
        自己完結した HTML 文書文字列。
    """
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        "<title>ears-trace Traceability Report</title>\n"
        f"<style>\n{_INLINE_CSS}</style>\n"
        "</head>\n"
        "<body>\n"
        "<h1>Traceability Report</h1>\n"
        f"{_summary_html(report)}\n"
        f"{_table_html(report)}\n"
        f"{_meta_html(report)}\n"
        "</body>\n"
        "</html>\n"
    )
