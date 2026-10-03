"""CLI を介した end-to-end 統合テストと自ツール自己カバレッジの担保。

対象要件: R-40, R-45, R-46, R-47, R-48, R-49、および R-29/R-30（HTML 埋め込み）。
加えて R-38（サブコマンド未指定の非ゼロ終了）を統合観点で確認する。

本モジュールは `ears_trace.cli.main` を唯一の入口として駆動し、ドメイン純粋関数と
副作用（ファイルI/O・終了コード）の結線が実運用シナリオで成立することを検証する。

report-format ステアリング規約に従い、各テストへ requirement マーカーと
docstring の `req:` タグを付与し、自ツールで再リンク可能にする。
AAA（Arrange-Act-Assert）パターンで記述する。
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from ears_trace.cli import main
from ears_trace.coverage import build_report
from ears_trace.linker import extract_links_from_paths
from ears_trace.parser import parse

# 本リポジトリのルート（tests/ の 1 つ上）。自己トレーサビリティ検証で使用する。
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
# 本 spec の要件文書と、リンク抽出に用いるプロジェクトの tests/ ディレクトリ。
_SPEC_REQUIREMENTS = _PROJECT_ROOT / ".kiro" / "specs" / "ears-trace" / "requirements.md"
_PROJECT_TESTS_DIR = _PROJECT_ROOT / "tests"

# ---------------------------------------------------------------------------
# 補助: テスト用の合成要件文書とテストファイル
# ---------------------------------------------------------------------------

# 2 件の要件を持つ最小の要件文書（いずれも明示ID付き）。
_REQ_DOC = """\
# 要件

- R-01: THE SYSTEM SHALL do foo
- R-02: WHEN x THE SYSTEM SHALL do bar
"""

# 64 桁の小文字 16 進数（SHA-256）を検出する正規表現。
_SHA256_HEX = re.compile(r"\b[0-9a-f]{64}\b")


def _write_requirements(tmp_path: Path, text: str = _REQ_DOC) -> Path:
    """要件文書ファイルを作成してパスを返す補助。"""
    path = tmp_path / "requirements.md"
    path.write_text(text, encoding="utf-8")
    return path


def _write_tests_dir(tmp_path: Path, *, covered_ids: tuple[str, ...]) -> Path:
    """指定要件を covered にするテストディレクトリを作成して返す補助。

    各要件へ requirement マーカーを付けた `test_sample.py` を 1 つ用意する。
    """
    tests_dir = tmp_path / "linked_tests"
    tests_dir.mkdir(parents=True)
    lines = ["import pytest", ""]
    for index, req_id in enumerate(covered_ids):
        lines.append(f'@pytest.mark.requirement("{req_id}")')
        lines.append(f"def test_sample_{index}() -> None:")
        lines.append("    pass")
        lines.append("")
    (tests_dir / "test_sample.py").write_text("\n".join(lines), encoding="utf-8")
    return tests_dir


# ---------------------------------------------------------------------------
# R-40: report→generate→check のハッピーパス end-to-end
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.requirement("R-40")
def test_report_generate_check_happy_path(tmp_path: Path) -> None:
    """report・generate・check を連続実行し、穴あり検出まで一貫動作する。

    req: R-40
    """
    # Arrange: R-01 のみ covered（R-02 は gap）
    req_path = _write_requirements(tmp_path)
    tests_dir = _write_tests_dir(tmp_path, covered_ids=("R-01",))
    html_path = tmp_path / "out" / "traceability.html"
    stub_path = tmp_path / "generated" / "test_stubs.py"

    # Act / Assert: report は HTML を書き終了コード 0
    report_code = main(
        ["report", "-r", str(req_path), "--tests", str(tests_dir), "-o", str(html_path)]
    )
    assert report_code == 0
    assert html_path.exists()
    assert html_path.read_text(encoding="utf-8").strip() != ""

    # Act / Assert: generate はスタブを書き終了コード 0
    generate_code = main(
        ["generate", "-r", str(req_path), "--tests", str(tests_dir), "-o", str(stub_path)]
    )
    assert generate_code == 0
    assert stub_path.exists()

    # Act / Assert: 既定 min-coverage=1.0 で穴（R-02）があるため 1
    check_gap_code = main(["check", "-r", str(req_path), "--tests", str(tests_dir)])
    assert check_gap_code == 1

    # Act / Assert: 閾値を 0.0 に緩めれば 0
    check_pass_code = main(
        ["check", "-r", str(req_path), "--tests", str(tests_dir), "--min-coverage", "0.0"]
    )
    assert check_pass_code == 0


# ---------------------------------------------------------------------------
# R-29, R-30: HTML への入力ハッシュと UTC 生成時刻の埋め込み
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.requirement("R-29")
def test_report_html_embeds_input_hash_and_timestamp(tmp_path: Path) -> None:
    """生成 HTML に入力の SHA-256 と UTC 生成時刻が埋め込まれる。

    req: R-29
    """
    # Arrange
    req_path = _write_requirements(tmp_path)
    html_path = tmp_path / "report.html"

    # Act
    exit_code = main(["report", "-r", str(req_path), "-o", str(html_path)])

    # Assert: マーカー文字列と 64 桁 16 進ハッシュの存在を確認する
    assert exit_code == 0
    html = html_path.read_text(encoding="utf-8")
    assert "Input SHA-256:" in html
    assert "Generated at (UTC):" in html

    # 入力テキストの SHA-256 がそのまま埋め込まれていることを確認する。
    expected_hash = hashlib.sha256(req_path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
    assert expected_hash in html

    # 「Input SHA-256:」以降に 64 桁の小文字 16 進が現れることも頑健に確認する。
    tail = html.split("Input SHA-256:", 1)[1]
    assert _SHA256_HEX.search(tail) is not None


# ---------------------------------------------------------------------------
# R-42（統合）: 全件 covered なら check は既定閾値で 0
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.requirement("R-42")
def test_check_returns_zero_when_fully_covered(tmp_path: Path) -> None:
    """全要件が covered なら既定 min-coverage=1.0 で終了コード 0 を返す。

    req: R-42
    """
    # Arrange: R-01/R-02 の両方を covered にする
    req_path = _write_requirements(tmp_path)
    tests_dir = _write_tests_dir(tmp_path, covered_ids=("R-01", "R-02"))

    # Act
    exit_code = main(["check", "-r", str(req_path), "--tests", str(tests_dir)])

    # Assert
    assert exit_code == 0


# ---------------------------------------------------------------------------
# R-45: 空の要件入力でもクラッシュしない
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.requirement("R-45")
def test_empty_requirements_does_not_crash(tmp_path: Path) -> None:
    """空の要件文書でも report は HTML を書き、check も停止せず 0 を返す。

    req: R-45
    """
    # Arrange: 空ファイル（要件 0 件）
    req_path = _write_requirements(tmp_path, text="")
    html_path = tmp_path / "report.html"

    # Act
    report_code = main(["report", "-r", str(req_path), "-o", str(html_path)])
    check_code = main(["check", "-r", str(req_path)])

    # Assert: 例外停止せず、uncovered が無いため check は 0
    assert report_code == 0
    assert html_path.exists()
    assert check_code == 0


# ---------------------------------------------------------------------------
# R-46: SHALL を含まない非要件入力でもクラッシュしない
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.requirement("R-46")
def test_non_requirement_input_does_not_crash(tmp_path: Path) -> None:
    """SHALL を含まない散文のみの入力でも report/check が停止せず 0 を返す。

    req: R-46
    """
    # Arrange: 要件行（SHALL）を一切含まない散文
    prose = "これは単なる説明文です。\n要件は含まれていません。\n"
    req_path = _write_requirements(tmp_path, text=prose)
    html_path = tmp_path / "report.html"

    # Act
    report_code = main(["report", "-r", str(req_path), "-o", str(html_path)])
    check_code = main(["check", "-r", str(req_path)])

    # Assert
    assert report_code == 0
    assert html_path.exists()
    assert check_code == 0


# ---------------------------------------------------------------------------
# R-49: 存在しない --tests ディレクトリはテスト無し扱い（クラッシュしない）
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.requirement("R-49")
def test_missing_tests_dir_does_not_crash(tmp_path: Path) -> None:
    """存在しない --tests でも report は 0、check は全件 gap で 1 を返す。

    req: R-49
    """
    # Arrange: --tests に存在しないパスを渡す
    req_path = _write_requirements(tmp_path)
    missing_dir = tmp_path / "does_not_exist"
    assert not missing_dir.exists()
    html_path = tmp_path / "report.html"

    # Act: 例外停止しないことを確認する
    report_code = main(
        ["report", "-r", str(req_path), "--tests", str(missing_dir), "-o", str(html_path)]
    )
    check_code = main(["check", "-r", str(req_path), "--tests", str(missing_dir)])

    # Assert: report は 0、全件 uncovered（0.0 < 既定 1.0）なので check は 1
    assert report_code == 0
    assert html_path.exists()
    assert check_code == 1


# ---------------------------------------------------------------------------
# R-47, R-48: 解析不能/復号不能なテストファイルはスキップし良い link は残る
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.requirement("R-47")
@pytest.mark.requirement("R-48")
def test_broken_and_undecodable_test_files_are_skipped(tmp_path: Path) -> None:
    """構文破損(R-47)・UTF-8 復号不能(R-48)のテストは飛ばし、良い link は有効。

    req: R-47
    req: R-48
    """
    # Arrange: 良い test_good.py で R-01 を covered にしつつ、壊れたファイルを混在させる
    req_path = _write_requirements(tmp_path)
    tests_dir = tmp_path / "mixed_tests"
    tests_dir.mkdir()

    good = tests_dir / "test_good.py"
    good.write_text(
        'import pytest\n\n\n@pytest.mark.requirement("R-01")\ndef test_good() -> None:\n    pass\n',
        encoding="utf-8",
    )

    # 構文破損ファイル（AST 解析が SyntaxError になる）。
    (tests_dir / "test_broken.py").write_text("def test_x(:\n    pass\n", encoding="utf-8")

    # 不正な UTF-8 バイト列（復号不能）。
    (tests_dir / "test_bad.py").write_bytes(b"\xff\xfe\x00\x01def test_y():\n")

    # Act: 壊れたファイルがあっても停止せず、良い link は生きている
    report_code = main(
        ["report", "-r", str(req_path), "--tests", str(tests_dir), "-o", str(tmp_path / "r.html")]
    )
    # R-01 のみ covered（2 件中 1 件 = 0.5）。閾値 0.5 なら 0 を返すはず。
    check_code = main(
        ["check", "-r", str(req_path), "--tests", str(tests_dir), "--min-coverage", "0.5"]
    )

    # Assert: 例外停止せず int を返し、良い link で R-01 が covered 扱いになっている
    assert report_code == 0
    assert isinstance(check_code, int)
    assert check_code == 0


# ---------------------------------------------------------------------------
# R-38（統合）: サブコマンド未指定は SystemExit を送出する
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.requirement("R-38")
def test_missing_subcommand_raises_system_exit() -> None:
    """サブコマンド未指定で起動すると SystemExit を送出する。

    req: R-38
    """
    # Act / Assert
    with pytest.raises(SystemExit):
        main([])


# ---------------------------------------------------------------------------
# 自己トレーサビリティ（ドッグフーディング）: ears-trace 自身の spec 要件が
# 本リポジトリのテスト群で網羅されていることを確認する。
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.requirement("R-40")
def test_self_traceability_all_real_requirements_covered() -> None:
    """ears-trace を自分自身の spec に適用し、実要件 R-01〜R-50 が全て covered。

    本 spec の requirements.md と本リポジトリの tests/ を入力に、ears-trace の
    ドメインパイプライン（parse → link 抽出 → 集計）を駆動する。実際に定義された
    50 件の要件（R-01〜R-50）が 1 件残らずテストに紐づく（covered）ことを検証し、
    自己トレーサビリティ（ドッグフーディングの自己整合）を担保する。

    KI-01 の修正により、Glossary 等でインラインコード（バッククォート内）に
    `SHALL` を含むだけの説明文は要件行として抽出されない。したがって擬似要件は
    発生せず、要件は実在する R-01〜R-50 の 50 件ちょうどになる。

    req: R-40
    """
    # Arrange: 自 spec の要件文書と自リポジトリの test_*.py を収集する
    assert _SPEC_REQUIREMENTS.is_file()
    assert _PROJECT_TESTS_DIR.is_dir()
    requirements_text = _SPEC_REQUIREMENTS.read_text(encoding="utf-8")
    requirements = parse(requirements_text)
    test_paths = sorted(_PROJECT_TESTS_DIR.rglob("test_*.py"))
    links_by_requirement = extract_links_from_paths(test_paths)

    # Act: 自ツールの集計で CoverageReport を構築する
    report = build_report(requirements, links_by_requirement, input_text=requirements_text)

    # Assert: 実在する受け入れ基準 R-01〜R-50 がすべて covered である
    real_requirement_ids = {f"R-{number:02d}" for number in range(1, 51)}
    missing = sorted(real_requirement_ids - report.covered_ids)
    assert missing == [], f"未カバレッジの実要件が存在する: {missing}"

    # 擬似要件は発生せず、uncovered は存在しない（自己カバレッジ 100%）
    assert report.uncovered_ids == frozenset()


@pytest.mark.integration
@pytest.mark.requirement("R-40")
def test_self_check_cli_exit_code_is_zero_at_full_coverage() -> None:
    """自 spec への `check` CLI は、既定閾値(1.0)でも終了コード 0 を返す。

    KI-01 修正後は擬似要件が発生せず、実要件 R-01〜R-50 がすべて covered なので
    自己カバレッジは 50/50（100%）になる。したがって既定 min-coverage=1.0 でも
    穴は無く、終了コード 0 を返す。より緩い閾値 0.8 でも当然 0 を返す。
    これにより「ツールが自分の全実要件を covered と報告する」ことを CLI で確認する。

    req: R-40
    """
    # Arrange: 自 spec の要件文書と自リポジトリの tests/ を CLI 引数に用いる
    req_arg = str(_SPEC_REQUIREMENTS)
    tests_arg = str(_PROJECT_TESTS_DIR)

    # Act: 既定閾値（1.0）と、より緩い閾値（0.8）で判定する
    strict_code = main(["check", "-r", req_arg, "--tests", tests_arg])
    tolerant_code = main(["check", "-r", req_arg, "--tests", tests_arg, "--min-coverage", "0.8"])

    # Assert: 全要件 covered のため、どちらの閾値でも終了コード 0
    assert strict_code == 0
    assert tolerant_code == 0
