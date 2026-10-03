"""cli モジュールのサブコマンド・終了コード・出力のユニット/統合テスト。

対象要件: R-37, R-38, R-39, R-40, R-41, R-42, R-43, R-44, R-49。
CLI 層は副作用（ファイルI/O・標準出力・終了コード・argparse）の唯一の集約点であり、
ドメイン純粋関数を組み合わせて end-to-end の挙動を検証する。

report-format ステアリング規約に従い、各テストへ requirement マーカーと
docstring の `req:` タグを付与し、自ツールで再リンク可能にする。
AAA（Arrange-Act-Assert）パターンで記述する。
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from ears_trace.cli import build_parser, main

# ---------------------------------------------------------------------------
# 補助: テスト用の合成要件文書とテストファイル
# ---------------------------------------------------------------------------

# 2 件の要件を持つ最小の要件文書（いずれも明示ID付き）。
_REQ_DOC = """\
- R-01: THE SYSTEM SHALL do foo
- R-02: WHEN x THE SYSTEM SHALL do bar
"""


def _write_requirements(tmp_path: Path, text: str = _REQ_DOC) -> Path:
    """要件文書ファイルを作成してパスを返す補助。"""
    path = tmp_path / "requirements.md"
    path.write_text(text, encoding="utf-8")
    return path


def _write_tests_dir(tmp_path: Path, *, covered_ids: tuple[str, ...]) -> Path:
    """指定要件を covered にするテストディレクトリを作成して返す補助。

    `test_*.py` を再帰収集対象として作り、各要件に requirement マーカーを付けた
    テスト関数を 1 つ用意する（R-40 検証用）。
    """
    tests_dir = tmp_path / "linked_tests"
    nested = tests_dir / "nested"
    nested.mkdir(parents=True)
    lines = ["import pytest", ""]
    for index, req_id in enumerate(covered_ids):
        lines.append(f'@pytest.mark.requirement("{req_id}")')
        lines.append(f"def test_linked_{index}() -> None:")
        lines.append("    pass")
        lines.append("")
    # 再帰収集を確認するため、ネストした階層に配置する。
    (nested / "test_linked.py").write_text("\n".join(lines), encoding="utf-8")
    return tests_dir


@pytest.fixture
def chdir_tmp(tmp_path: Path) -> Iterator[Path]:
    """既定出力パス（相対）を検証するため CWD を tmp_path に移すフィクスチャ。"""
    original = Path.cwd()
    os.chdir(tmp_path)
    try:
        yield tmp_path
    finally:
        os.chdir(original)


# ---------------------------------------------------------------------------
# R-37: 3 サブコマンドの提供
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-37")
def test_build_parser_exposes_three_subcommands() -> None:
    """build_parser が report・check・generate の 3 サブコマンドを公開する。

    req: R-37
    """
    # Arrange
    parser = build_parser()

    # Act: サブパーサの choices を収集する
    subparser_actions = [
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    ]

    # Assert
    assert len(subparser_actions) == 1
    choices = set(subparser_actions[0].choices)
    assert choices == {"report", "check", "generate"}


# ---------------------------------------------------------------------------
# R-38: サブコマンド未指定はエラー（非ゼロ終了）
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.requirement("R-38")
def test_main_without_subcommand_exits_nonzero() -> None:
    """サブコマンド未指定で起動すると非ゼロ終了する（クラッシュしない）。

    req: R-38
    """
    # Act / Assert: argparse が SystemExit(非ゼロ) を送出する
    with pytest.raises(SystemExit) as exc_info:
        main([])

    code = exc_info.value.code
    assert code is not None
    assert code != 0


# ---------------------------------------------------------------------------
# R-39: report が既定/指定パスへ HTML を書き終了コード 0
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.requirement("R-39")
def test_report_writes_default_output_and_returns_zero(chdir_tmp: Path) -> None:
    """report は既定 out/traceability.html へ HTML を書き、終了コード 0 を返す。

    req: R-39
    """
    # Arrange
    req_path = _write_requirements(chdir_tmp)

    # Act
    exit_code = main(["report", "--requirements", str(req_path)])

    # Assert
    assert exit_code == 0
    output = chdir_tmp / "out" / "traceability.html"
    assert output.exists()
    assert "<!DOCTYPE html>" in output.read_text(encoding="utf-8")


@pytest.mark.integration
@pytest.mark.requirement("R-39")
def test_report_writes_custom_output_path(tmp_path: Path) -> None:
    """report は -o/--output で指定したパスへ HTML を書き終了コード 0 を返す。

    req: R-39
    """
    # Arrange
    req_path = _write_requirements(tmp_path)
    out_path = tmp_path / "custom_report.html"

    # Act
    exit_code = main(["report", "--requirements", str(req_path), "-o", str(out_path)])

    # Assert
    assert exit_code == 0
    assert out_path.exists()
    assert "<html" in out_path.read_text(encoding="utf-8").lower()


# ---------------------------------------------------------------------------
# R-43: generate が既定/指定パスへスタブを書き終了コード 0
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.requirement("R-43")
def test_generate_writes_default_output_and_returns_zero(chdir_tmp: Path) -> None:
    """generate は既定 tests/test_generated_stubs.py へ書き終了コード 0 を返す。

    req: R-43
    """
    # Arrange
    req_path = _write_requirements(chdir_tmp)

    # Act
    exit_code = main(["generate", "--requirements", str(req_path)])

    # Assert
    assert exit_code == 0
    output = chdir_tmp / "tests" / "test_generated_stubs.py"
    assert output.exists()
    content = output.read_text(encoding="utf-8")
    # 未充足要件（テスト無し）のスタブが含まれる。
    assert "import pytest" in content
    assert "pytest.mark.requirement" in content


@pytest.mark.integration
@pytest.mark.requirement("R-43")
def test_generate_writes_custom_output_path(tmp_path: Path) -> None:
    """generate は -o/--output で指定したパスへスタブを書き終了コード 0 を返す。

    req: R-43
    """
    # Arrange
    req_path = _write_requirements(tmp_path)
    out_path = tmp_path / "stubs" / "my_stubs.py"

    # Act
    exit_code = main(["generate", "--requirements", str(req_path), "--output", str(out_path)])

    # Assert
    assert exit_code == 0
    assert out_path.exists()
    assert "import pytest" in out_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# R-44: 出力先の親ディレクトリ自動作成
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.requirement("R-44")
def test_report_creates_missing_parent_directories(tmp_path: Path) -> None:
    """report は出力先の親ディレクトリが無ければ作成する。

    req: R-44
    """
    # Arrange: 存在しない深いネストのパスを指定する
    req_path = _write_requirements(tmp_path)
    out_path = tmp_path / "a" / "b" / "c" / "report.html"
    assert not out_path.parent.exists()

    # Act
    exit_code = main(["report", "--requirements", str(req_path), "-o", str(out_path)])

    # Assert
    assert exit_code == 0
    assert out_path.exists()


@pytest.mark.integration
@pytest.mark.requirement("R-44")
def test_generate_creates_missing_parent_directories(tmp_path: Path) -> None:
    """generate は出力先の親ディレクトリが無ければ作成する。

    req: R-44
    """
    # Arrange
    req_path = _write_requirements(tmp_path)
    out_path = tmp_path / "x" / "y" / "z" / "stubs.py"
    assert not out_path.parent.exists()

    # Act
    exit_code = main(["generate", "--requirements", str(req_path), "-o", str(out_path)])

    # Assert
    assert exit_code == 0
    assert out_path.exists()


# ---------------------------------------------------------------------------
# R-40: --tests 配下の test_*.py を再帰収集してリンク抽出に用いる
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.requirement("R-40")
def test_check_collects_tests_recursively_for_links(tmp_path: Path) -> None:
    """--tests 配下（ネスト含む）の test_*.py を収集し要件を covered にする。

    req: R-40
    """
    # Arrange: R-01/R-02 の両方を covered にするテストディレクトリ
    req_path = _write_requirements(tmp_path)
    tests_dir = _write_tests_dir(tmp_path, covered_ids=("R-01", "R-02"))

    # Act: 全件 covered なので check は 0 を返すはず（R-42 連携）
    exit_code = main(
        [
            "check",
            "--requirements",
            str(req_path),
            "--tests",
            str(tests_dir),
        ]
    )

    # Assert: ネストした test_*.py が収集されリンクが成立している
    assert exit_code == 0


# ---------------------------------------------------------------------------
# R-41: 穴あり & 閾値未満で非ゼロ終了（既定 --min-coverage=1.0）
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.requirement("R-41")
def test_check_returns_one_when_uncovered_below_threshold(tmp_path: Path) -> None:
    """uncovered が存在しカバレッジ率が閾値未満のとき終了コード 1 を返す。

    req: R-41
    """
    # Arrange: R-01 のみ covered（2 件中 1 件 = 0.5 < 既定 1.0）
    req_path = _write_requirements(tmp_path)
    tests_dir = _write_tests_dir(tmp_path, covered_ids=("R-01",))

    # Act: --min-coverage 未指定 → 既定 1.0 を適用
    exit_code = main(
        [
            "check",
            "--requirements",
            str(req_path),
            "--tests",
            str(tests_dir),
        ]
    )

    # Assert
    assert exit_code == 1


@pytest.mark.unit
@pytest.mark.requirement("R-41")
def test_check_default_min_coverage_is_one() -> None:
    """check の --min-coverage 既定値は 1.0 である。

    req: R-41
    """
    # Arrange
    parser = build_parser()

    # Act
    namespace = parser.parse_args(["check", "--requirements", "dummy.md"])

    # Assert
    assert namespace.min_coverage == 1.0


# ---------------------------------------------------------------------------
# R-42: 穴なし or 閾値以上で終了コード 0
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.requirement("R-42")
def test_check_returns_zero_when_fully_covered(tmp_path: Path) -> None:
    """uncovered が無い（全件 covered）とき終了コード 0 を返す。

    req: R-42
    """
    # Arrange: 全要件 covered
    req_path = _write_requirements(tmp_path)
    tests_dir = _write_tests_dir(tmp_path, covered_ids=("R-01", "R-02"))

    # Act
    exit_code = main(["check", "--requirements", str(req_path), "--tests", str(tests_dir)])

    # Assert
    assert exit_code == 0


@pytest.mark.integration
@pytest.mark.requirement("R-42")
def test_check_returns_zero_when_rate_meets_threshold(tmp_path: Path) -> None:
    """uncovered が残っていてもカバレッジ率が閾値以上なら終了コード 0 を返す。

    req: R-42
    """
    # Arrange: 2 件中 1 件 covered（0.5）、閾値を 0.5 に緩める
    req_path = _write_requirements(tmp_path)
    tests_dir = _write_tests_dir(tmp_path, covered_ids=("R-01",))

    # Act
    exit_code = main(
        [
            "check",
            "--requirements",
            str(req_path),
            "--tests",
            str(tests_dir),
            "--min-coverage",
            "0.5",
        ]
    )

    # Assert
    assert exit_code == 0


# ---------------------------------------------------------------------------
# R-49: 存在しない --tests ディレクトリはテスト無し扱い（クラッシュしない）
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.requirement("R-49")
def test_check_missing_tests_dir_treated_as_no_tests(tmp_path: Path) -> None:
    """存在しない --tests ディレクトリは全要件 uncovered 扱いで停止しない。

    req: R-49
    """
    # Arrange: --tests に存在しないパスを渡す
    req_path = _write_requirements(tmp_path)
    missing_dir = tmp_path / "does_not_exist"
    assert not missing_dir.exists()

    # Act: 全件 uncovered（0.0 < 既定 1.0）なので非ゼロ終了するが、クラッシュしない
    exit_code = main(["check", "--requirements", str(req_path), "--tests", str(missing_dir)])

    # Assert: 例外停止せず、穴ありとして 1 を返す
    assert exit_code == 1


@pytest.mark.integration
@pytest.mark.requirement("R-49")
def test_report_missing_tests_dir_does_not_crash(tmp_path: Path) -> None:
    """report でも存在しない --tests は停止せず HTML を生成する（全件 gap）。

    req: R-49
    """
    # Arrange
    req_path = _write_requirements(tmp_path)
    out_path = tmp_path / "report.html"

    # Act
    exit_code = main(
        [
            "report",
            "--requirements",
            str(req_path),
            "--tests",
            str(tmp_path / "nope"),
            "-o",
            str(out_path),
        ]
    )

    # Assert
    assert exit_code == 0
    assert out_path.exists()
    assert "gap" in out_path.read_text(encoding="utf-8").lower()



# ---------------------------------------------------------------------------
# L6: report --enrich で MCP取得の注釈JSONをレポートへ反映する
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.requirement("R-50")
def test_report_enrich_embeds_annotations_from_json(tmp_path: Path) -> None:
    """--enrich に注釈JSON（MCP取得結果）を渡すと、説明がレポートに入る。

    fetch MCP が取得・保存した注釈JSONを ears-trace が実行時に読み込む経路（L6）。
    req: R-50
    """
    # Arrange
    import json

    req_path = _write_requirements(tmp_path)
    out_path = tmp_path / "report.html"
    annotations_path = tmp_path / "annotations.json"
    annotations_path.write_text(
        json.dumps(
            {"UBIQUITOUS": "常時要件の説明(MCP)", "EVENT": "イベント要件の説明(MCP)"},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # Act
    exit_code = main(
        [
            "report",
            "--requirements",
            str(req_path),
            "-o",
            str(out_path),
            "--enrich",
            str(annotations_path),
        ]
    )

    # Assert
    assert exit_code == 0
    content = out_path.read_text(encoding="utf-8")
    assert "常時要件の説明(MCP)" in content
    assert "イベント要件の説明(MCP)" in content


@pytest.mark.integration
@pytest.mark.requirement("R-50")
def test_report_enrich_missing_json_falls_back_without_crash(tmp_path: Path) -> None:
    """--enrich に存在しないJSONを指定しても、クラッシュせず通常レポートを出す。

    MCP取得結果が無い環境でも処理を継続する（R-50 頑健性）。
    req: R-50
    """
    # Arrange
    req_path = _write_requirements(tmp_path)
    out_path = tmp_path / "report.html"
    missing = tmp_path / "no_such_annotations.json"

    # Act
    exit_code = main(
        [
            "report",
            "--requirements",
            str(req_path),
            "-o",
            str(out_path),
            "--enrich",
            str(missing),
        ]
    )

    # Assert: 落ちずに0、HTMLは生成される
    assert exit_code == 0
    assert out_path.exists()
    assert "<!DOCTYPE html>" in out_path.read_text(encoding="utf-8")



# ---------------------------------------------------------------------------
# python -m ears_trace.cli で main() が実行される（__main__ ガード）
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.requirement("R-37")
def test_module_execution_invokes_main(tmp_path: Path) -> None:
    """`python -m ears_trace.cli` 実行で main() が呼ばれ、レポートが生成される。

    PyPI等に依存できない環境でも、依存なしの標準実行経路で動くことを保証する。
    __main__ ガードが無いと EXIT=0 でも何も生成されない退行を防ぐ。
    req: R-37
    """
    # Arrange
    import subprocess
    import sys

    req_path = _write_requirements(tmp_path)
    out_path = tmp_path / "traceability.html"
    project_src = Path(__file__).resolve().parents[1] / "src"

    # Act: サブプロセスで python -m ears_trace.cli を実行
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ears_trace.cli",
            "report",
            "--requirements",
            str(req_path),
            "-o",
            str(out_path),
        ],
        cwd=tmp_path,
        env={"PYTHONPATH": str(project_src)},
        capture_output=True,
        text=True,
    )

    # Assert: 正常終了し、HTMLが実際に生成される
    assert result.returncode == 0, result.stderr
    assert out_path.exists()
    assert "<!DOCTYPE html>" in out_path.read_text(encoding="utf-8")
