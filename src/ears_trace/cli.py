"""ears-trace の CLI エントリポイント（要件6: R-37〜R-44）。

本モジュールは副作用（ファイルI/O・標準出力・終了コード・argparse）の唯一の
集約点であり、ドメイン純粋関数（parser / linker / coverage / report /
stub_generator）を組み合わせて 3 サブコマンド（report・check・generate）を提供する。

- `report`: HTML レポートを既定 `out/traceability.html` へ書き出す（R-39）。
- `check` : カバレッジ判定を行い、穴あり & 閾値未満なら非ゼロ終了する（R-41, R-42）。
- `generate`: 未充足要件向けスタブを既定 `tests/test_generated_stubs.py` へ書く（R-43）。

頑健性のため、存在しない `--tests` ディレクトリはテスト無し（全要件 uncovered）
として扱い停止しない（R-49）。出力時は親ディレクトリを自動作成する（R-44）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ears_trace.coverage import build_report
from ears_trace.enrich import DEFAULT_DESCRIPTIONS, load_annotations
from ears_trace.linker import extract_links_from_paths
from ears_trace.models import CoverageReport
from ears_trace.parser import parse
from ears_trace.report import render_html
from ears_trace.stub_generator import generate_stubs

# 既定の出力先（R-39, R-43）。相対パスとして解決され、CWD 基準で書き出す。
_DEFAULT_REPORT_OUTPUT = Path("out/traceability.html")
_DEFAULT_STUB_OUTPUT = Path("tests/test_generated_stubs.py")
# check の既定カバレッジ閾値（R-41）。
_DEFAULT_MIN_COVERAGE = 1.0


def build_parser() -> argparse.ArgumentParser:
    """3 サブコマンドを持つ argparse パーサを構築する（R-37, R-38）。

    `report`・`check`・`generate` の 3 サブコマンドを公開し、サブコマンドを必須に
    する（`required=True`）ことで、未指定起動時に argparse が非ゼロ終了する（R-38）。

    Returns:
        構築済みの ArgumentParser。
    """
    parser = argparse.ArgumentParser(
        prog="ears-trace",
        description="EARS 要件からテスト・トレーサビリティを可視化する CLI",
    )
    # サブコマンド必須（未指定なら argparse がエラー終了する）（R-38）。
    subparsers = parser.add_subparsers(dest="command", required=True)

    # report サブコマンド（R-39）。
    report_parser = subparsers.add_parser("report", help="トレーサビリティ HTML レポートを生成する")
    _add_requirements_arg(report_parser)
    _add_tests_arg(report_parser)
    report_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=_DEFAULT_REPORT_OUTPUT,
        help=f"HTML 出力先（既定: {_DEFAULT_REPORT_OUTPUT}）",
    )
    report_parser.add_argument(
        "--enrich",
        type=Path,
        default=None,
        metavar="ANNOTATIONS_JSON",
        help=(
            "EARSパターン注釈JSON（MCP(fetch)で取得・保存した説明）を読み込み、"
            "レポートに併記する。読み込めない場合は内蔵の既定説明にフォールバックする"
        ),
    )

    # check サブコマンド（R-40, R-41, R-42）。
    check_parser = subparsers.add_parser("check", help="カバレッジ判定を行い終了コードで結果を返す")
    _add_requirements_arg(check_parser)
    _add_tests_arg(check_parser)
    check_parser.add_argument(
        "--min-coverage",
        type=float,
        default=_DEFAULT_MIN_COVERAGE,
        help=f"許容する最小カバレッジ率（既定: {_DEFAULT_MIN_COVERAGE}）",
    )

    # generate サブコマンド（R-43）。
    generate_parser = subparsers.add_parser(
        "generate", help="未充足要件向けの pytest スタブを生成する"
    )
    _add_requirements_arg(generate_parser)
    _add_tests_arg(generate_parser)
    generate_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=_DEFAULT_STUB_OUTPUT,
        help=f"スタブ出力先（既定: {_DEFAULT_STUB_OUTPUT}）",
    )

    return parser


def _add_requirements_arg(parser: argparse.ArgumentParser) -> None:
    """全サブコマンド共通の `--requirements`（要件文書パス）を追加する。"""
    parser.add_argument(
        "-r",
        "--requirements",
        type=Path,
        required=True,
        help="EARS 要件文書のパス",
    )


def _add_tests_arg(parser: argparse.ArgumentParser) -> None:
    """全サブコマンド共通の `--tests`（テストディレクトリ）を追加する（R-40）。"""
    parser.add_argument(
        "--tests",
        type=Path,
        default=None,
        help="リンク抽出に用いるテストディレクトリ（配下の test_*.py を再帰収集）",
    )


def _collect_test_paths(tests_dir: Path | None) -> list[Path]:
    """`--tests` 配下の `test_*.py` を再帰収集する（R-40, R-49）。

    ディレクトリが未指定・非存在・非ディレクトリの場合は空リストを返し、
    テスト無し（全要件 uncovered）として扱えるようにする（R-49）。

    Args:
        tests_dir: `--tests` に指定されたパス。未指定なら None。

    Returns:
        収集した `test_*.py` のパス一覧（存在しなければ空）。
    """
    if tests_dir is None or not tests_dir.is_dir():
        return []  # 非存在・非ディレクトリはテスト無し扱い（R-49）
    return sorted(tests_dir.rglob("test_*.py"))


def _build_report_from_args(args: argparse.Namespace) -> CoverageReport:
    """コマンド引数から CoverageReport を構築する（副作用: 要件文書の読み取り）。

    要件文書を UTF-8 として読み取り、`parse` で要件を抽出する。`--tests` 配下の
    テストからリンクを抽出し、`build_report` で集計結果を構築する。SHA-256 の
    計算には要件文書の生テキストを用いる（R-29 連携）。

    Args:
        args: パース済みのコマンドライン引数。

    Returns:
        構築した不変の CoverageReport。
    """
    requirements_text = args.requirements.read_text(encoding="utf-8")
    requirements = parse(requirements_text)
    test_paths = _collect_test_paths(args.tests)
    links_by_requirement = extract_links_from_paths(test_paths)
    return build_report(
        requirements,
        links_by_requirement,
        input_text=requirements_text,
    )


def _write_output(output: Path, content: str) -> None:
    """出力先へ書き出す。親ディレクトリが無ければ作成する（R-44）。

    Args:
        output: 書き出し先パス。
        content: 書き出す本文。
    """
    output.parent.mkdir(parents=True, exist_ok=True)  # 親ディレクトリ自動作成（R-44）
    output.write_text(content, encoding="utf-8")


def _resolve_annotations(enrich_path: Path | None) -> dict[str, str] | None:
    """--enrich 指定時にレポートへ併記する注釈写像を解決する（L6, R-50）。

    MCP(fetch)が取得・保存した注釈JSONを読み込む。読み込めない場合は内蔵の
    既定説明（全EARSパターン）にフォールバックし、処理を中断しない（R-50）。
    --enrich 未指定なら None（注釈なし）を返す。

    Args:
        enrich_path: --enrich に渡された注釈JSONのパス。未指定なら None。

    Returns:
        EARSパターン値→説明文の写像、または None。
    """
    if enrich_path is None:
        return None
    loaded = load_annotations(enrich_path)
    if loaded is not None:
        return loaded
    # 読み込み失敗時は内蔵既定説明にフォールバック（R-50）。
    return {pattern.value: text for pattern, text in DEFAULT_DESCRIPTIONS.items()}


def _run_report(args: argparse.Namespace) -> int:
    """report サブコマンド本体: HTML を書き出し 0 を返す（R-39, R-44）。

    --enrich 指定時は注釈をレポートへ併記する（L6, R-50）。
    """
    report = _build_report_from_args(args)
    annotations = _resolve_annotations(getattr(args, "enrich", None))
    _write_output(args.output, render_html(report, annotations=annotations))
    return 0


def _run_generate(args: argparse.Namespace) -> int:
    """generate サブコマンド本体: スタブを書き出し 0 を返す（R-43, R-44）。"""
    report = _build_report_from_args(args)
    _write_output(args.output, generate_stubs(report))
    return 0


def _run_check(args: argparse.Namespace) -> int:
    """check サブコマンド本体: カバレッジ判定の終了コードを返す（R-41, R-42）。

    uncovered 要件が存在し、かつカバレッジ率が `--min-coverage` を下回る場合のみ
    非ゼロ（1）を返す（R-41）。uncovered が無い、またはカバレッジ率が閾値以上なら
    0 を返す（R-42）。

    Args:
        args: パース済みのコマンドライン引数。

    Returns:
        判定結果の終了コード（0 または 1）。
    """
    report = _build_report_from_args(args)
    has_uncovered = len(report.uncovered_ids) > 0
    below_threshold = report.coverage_rate < args.min_coverage
    if has_uncovered and below_threshold:
        return 1  # 穴あり & 閾値未満（R-41）
    return 0  # 穴なし or 閾値以上（R-42）


# サブコマンド名 → 実行関数のディスパッチ表。
_DISPATCH = {
    "report": _run_report,
    "check": _run_check,
    "generate": _run_generate,
}


def main(argv: list[str] | None = None) -> int:
    """CLI エントリポイント。終了コードを返す（R-37〜R-44）。

    `argv` を解析してサブコマンドへディスパッチする。サブコマンド未指定の場合は
    argparse が SystemExit（非ゼロ）を送出する（R-38）。正常系では終了コードを
    `int` として返し、自身では `sys.exit` を呼ばない（テスト容易性のため）。

    Args:
        argv: コマンドライン引数（None なら `sys.argv[1:]` を使用）。

    Returns:
        サブコマンド実行結果の終了コード。
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = _DISPATCH[args.command]
    return handler(args)


if __name__ == "__main__":
    # `python -m ears_trace.cli ...` での直接実行経路。
    # `ears-trace` コマンド（project.scripts）と同じく main() を呼び、
    # 終了コードをプロセスに伝播させる。
    sys.exit(main())
