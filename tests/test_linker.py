"""linker モジュールのリンク抽出のユニットテスト。

対象要件: R-11〜R-18（要件2: 要件ID⇔テストID のリンク抽出）と
頑健性の先取り R-47（構文解析不能ファイルのスキップ）・R-48（読取不能のスキップ）。
report-format ステアリング規約に従い、各テストへ requirement マーカーと
docstring の `req:` タグを付与し、自ツールで再リンク可能にする。
"""

from pathlib import Path

import pytest

from ears_trace.linker import extract_links_from_paths, extract_links_from_source

# ---------------------------------------------------------------------------
# 4.1 3方式のリンク抽出（R-11, R-12, R-13, R-14）
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.requirement("R-11")
def test_extracts_link_from_marker() -> None:
    """マーカー `@pytest.mark.requirement("R-01")` から要件IDを抽出する（R-11）。

    req: R-11
    """
    # Arrange
    source = "\n".join(
        [
            "import pytest",
            "",
            '@pytest.mark.requirement("R-01")',
            "def test_foo():",
            "    pass",
        ]
    )

    # Act
    links = extract_links_from_source(source, module="test_mod")

    # Assert
    assert links == {"R-01": ("test_mod::test_foo",)}


@pytest.mark.unit
@pytest.mark.requirement("R-11")
def test_extracts_multiple_marker_ids_from_single_test() -> None:
    """1テストに複数のマーカーがあれば全要件IDを抽出する（R-11）。

    req: R-11
    """
    # Arrange
    source = "\n".join(
        [
            "import pytest",
            "",
            '@pytest.mark.requirement("R-01")',
            '@pytest.mark.requirement("R-02")',
            "def test_foo():",
            "    pass",
        ]
    )

    # Act
    links = extract_links_from_source(source, module="test_mod")

    # Assert
    assert links["R-01"] == ("test_mod::test_foo",)
    assert links["R-02"] == ("test_mod::test_foo",)


@pytest.mark.unit
@pytest.mark.requirement("R-12")
def test_extracts_link_from_naming_convention() -> None:
    """命名規約 `test_r01_...` の関数名から要件IDを抽出する（R-12）。

    req: R-12
    """
    # Arrange
    source = "\n".join(
        [
            "def test_r01_something():",
            "    pass",
        ]
    )

    # Act
    links = extract_links_from_source(source, module="test_mod")

    # Assert
    assert links == {"R-01": ("test_mod::test_r01_something",)}


@pytest.mark.unit
@pytest.mark.requirement("R-13")
def test_extracts_link_from_docstring_tag() -> None:
    """docstring 内の `req: R-01` タグから要件IDを抽出する（R-13）。

    req: R-13
    """
    # Arrange
    source = "\n".join(
        [
            "def test_foo():",
            '    """何かを検証する。',
            "",
            "    req: R-01",
            '    """',
            "    pass",
        ]
    )

    # Act
    links = extract_links_from_source(source, module="test_mod")

    # Assert
    assert links == {"R-01": ("test_mod::test_foo",)}


@pytest.mark.unit
@pytest.mark.requirement("R-13")
def test_extracts_multiple_docstring_tags() -> None:
    """docstring に複数の `req:` タグがあれば全て抽出する（R-13）。

    req: R-13
    """
    # Arrange
    source = "\n".join(
        [
            "def test_foo():",
            '    """検証する。',
            "",
            "    req: R-01",
            "    req: R-02",
            '    """',
            "    pass",
        ]
    )

    # Act
    links = extract_links_from_source(source, module="test_mod")

    # Assert
    assert set(links) == {"R-01", "R-02"}


@pytest.mark.unit
@pytest.mark.requirement("R-14")
def test_normalizes_lowercase_id_from_marker() -> None:
    """マーカーの `r01` 表記を `R-01` に正規化する（R-14）。

    req: R-14
    """
    # Arrange
    source = "\n".join(
        [
            "import pytest",
            "",
            '@pytest.mark.requirement("r01")',
            "def test_foo():",
            "    pass",
        ]
    )

    # Act
    links = extract_links_from_source(source, module="test_mod")

    # Assert
    assert links == {"R-01": ("test_mod::test_foo",)}


@pytest.mark.unit
@pytest.mark.requirement("R-14")
def test_normalizes_id_without_hyphen() -> None:
    """docstring の `R1`（ハイフン無し・桁不足）を `R-01` に正規化する（R-14）。

    req: R-14
    """
    # Arrange
    source = "\n".join(
        [
            "def test_foo():",
            '    """req: R1"""',
            "    pass",
        ]
    )

    # Act
    links = extract_links_from_source(source, module="test_mod")

    # Assert
    assert links == {"R-01": ("test_mod::test_foo",)}


@pytest.mark.unit
@pytest.mark.requirement("R-14")
def test_normalizes_naming_convention_id() -> None:
    """命名規約 `test_r5_...` の `r5` を `R-05` に正規化する（R-14）。

    req: R-14
    """
    # Arrange
    source = "\n".join(
        [
            "def test_r5_case():",
            "    pass",
        ]
    )

    # Act
    links = extract_links_from_source(source, module="test_mod")

    # Assert
    assert links == {"R-05": ("test_mod::test_r5_case",)}


# ---------------------------------------------------------------------------
# 4.2 多対多・統合・整列（R-15, R-16, R-17, R-18, R-47）
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.requirement("R-15")
def test_single_test_multiple_requirements_preserved() -> None:
    """1テストが複数要件を宣言したら全リンクを保持する（R-15）。

    req: R-15
    """
    # Arrange: マーカー・命名規約・docstring を混在させ複数要件を宣言
    source = "\n".join(
        [
            "import pytest",
            "",
            '@pytest.mark.requirement("R-02")',
            "def test_r01_combo():",
            '    """req: R-03"""',
            "    pass",
        ]
    )

    # Act
    links = extract_links_from_source(source, module="test_mod")

    # Assert: 3方式それぞれの要件IDが同一テストに紐づく
    test_id = "test_mod::test_r01_combo"
    assert links["R-01"] == (test_id,)
    assert links["R-02"] == (test_id,)
    assert links["R-03"] == (test_id,)


@pytest.mark.unit
@pytest.mark.requirement("R-15")
def test_single_requirement_multiple_tests_preserved() -> None:
    """1要件に複数テストが紐づいたら全て保持する（R-15）。

    req: R-15
    """
    # Arrange
    source = "\n".join(
        [
            "import pytest",
            "",
            '@pytest.mark.requirement("R-01")',
            "def test_a():",
            "    pass",
            "",
            '@pytest.mark.requirement("R-01")',
            "def test_b():",
            "    pass",
        ]
    )

    # Act
    links = extract_links_from_source(source, module="test_mod")

    # Assert
    assert links["R-01"] == ("test_mod::test_a", "test_mod::test_b")


@pytest.mark.unit
@pytest.mark.requirement("R-15")
def test_non_requirement_decorators_are_ignored_in_many_to_many() -> None:
    """requirement 以外のデコレータは無視しつつ多対多リンクを保持する（R-15）。

    `@pytest.mark.skip`（引数なし Call でない属性）や
    `@pytest.mark.parametrize(...)`（requirement でない Call）が混在しても、
    requirement マーカーの複数要件リンクだけを正しく抽出する。

    req: R-15
    """
    # Arrange: ノイズとなる非 requirement デコレータを前後に挟む
    source = "\n".join(
        [
            "import pytest",
            "",
            "@pytest.mark.skip",
            '@pytest.mark.requirement("R-01")',
            '@pytest.mark.parametrize("x", [1, 2])',
            '@pytest.mark.requirement("R-02")',
            "def test_foo(x):",
            "    pass",
        ]
    )

    # Act
    links = extract_links_from_source(source, module="test_mod")

    # Assert: requirement 以外は無視され、R-01/R-02 の多対多が保持される
    assert links == {
        "R-01": ("test_mod::test_foo",),
        "R-02": ("test_mod::test_foo",),
    }


@pytest.mark.unit
@pytest.mark.requirement("R-16")
def test_test_id_uses_module_and_function_form() -> None:
    """テストIDは `モジュール名::テスト関数名` 形式で生成する（R-16）。

    req: R-16
    """
    # Arrange
    source = "\n".join(
        [
            "def test_r01_x():",
            "    pass",
        ]
    )

    # Act
    links = extract_links_from_source(source, module="tests.test_sample")

    # Assert
    assert links["R-01"] == ("tests.test_sample::test_r01_x",)


@pytest.mark.unit
@pytest.mark.requirement("R-16")
def test_class_methods_are_excluded() -> None:
    """クラス内のテストメソッドは対象外とする（R-16）。

    req: R-16
    """
    # Arrange: クラス内メソッドはトップレベル関数ではないので拾わない
    source = "\n".join(
        [
            "import pytest",
            "",
            "class TestGroup:",
            '    @pytest.mark.requirement("R-01")',
            "    def test_method(self):",
            '        """req: R-02"""',
            "        pass",
        ]
    )

    # Act
    links = extract_links_from_source(source, module="test_mod")

    # Assert
    assert links == {}


@pytest.mark.unit
@pytest.mark.requirement("R-47")
def test_unparsable_source_returns_empty_dict() -> None:
    """構文解析できないソースは空dictを返し中断しない（R-47）。

    req: R-47
    """
    # Arrange: 構文エラーを含むソース
    source = "def test_broken(:\n    pass"

    # Act
    links = extract_links_from_source(source, module="test_mod")

    # Assert
    assert links == {}


@pytest.mark.unit
@pytest.mark.requirement("R-46")
def test_non_test_functions_are_ignored() -> None:
    """`test_` 始まりでない関数はリンク抽出の対象外とする（R-46 の先取り）。

    req: R-46
    """
    # Arrange: マーカーは付くが関数名が test_ で始まらない
    source = "\n".join(
        [
            "import pytest",
            "",
            '@pytest.mark.requirement("R-01")',
            "def helper():",
            "    pass",
        ]
    )

    # Act
    links = extract_links_from_source(source, module="test_mod")

    # Assert
    assert links == {}


@pytest.mark.unit
@pytest.mark.requirement("R-17")
def test_merges_links_across_files(tmp_path: Path) -> None:
    """複数ファイルのリンクを要件ID単位で統合する（R-17）。

    req: R-17
    """
    # Arrange
    file_a = tmp_path / "test_a.py"
    file_a.write_text(
        "\n".join(
            [
                "import pytest",
                "",
                '@pytest.mark.requirement("R-01")',
                "def test_a():",
                "    pass",
            ]
        ),
        encoding="utf-8",
    )
    file_b = tmp_path / "test_b.py"
    file_b.write_text(
        "\n".join(
            [
                "def test_r01_b():",
                "    pass",
            ]
        ),
        encoding="utf-8",
    )

    # Act
    links = extract_links_from_paths([file_a, file_b])

    # Assert: R-01 は両ファイルのテストへ統合される
    assert links["R-01"] == ("test_a::test_a", "test_b::test_r01_b")


@pytest.mark.unit
@pytest.mark.requirement("R-18")
def test_deduplicates_and_sorts_test_ids(tmp_path: Path) -> None:
    """要件に紐づくテストIDを重複排除し整列して返す（R-18）。

    req: R-18
    """
    # Arrange: 同一要件へ複数方式・逆順で宣言し重複と乱れを作る
    file_a = tmp_path / "test_z.py"
    file_a.write_text(
        "\n".join(
            [
                "import pytest",
                "",
                '@pytest.mark.requirement("R-01")',
                "def test_r01_dup():",  # マーカーと命名規約の双方で R-01 を宣言（重複）
                "    pass",
            ]
        ),
        encoding="utf-8",
    )
    file_b = tmp_path / "test_a.py"
    file_b.write_text(
        "\n".join(
            [
                "def test_r01_early():",
                "    pass",
            ]
        ),
        encoding="utf-8",
    )

    # Act
    links = extract_links_from_paths([file_a, file_b])

    # Assert: 重複が排除され、テストIDが整列（sorted）されている
    test_ids = links["R-01"]
    assert test_ids == tuple(sorted(set(test_ids)))
    assert test_ids == ("test_a::test_r01_early", "test_z::test_r01_dup")


@pytest.mark.unit
@pytest.mark.requirement("R-48")
def test_unreadable_file_is_skipped(tmp_path: Path) -> None:
    """読み取れないファイルはスキップし処理を継続する（R-48）。

    req: R-48
    """
    # Arrange: 存在しないパスと正常ファイルを混在させる
    missing = tmp_path / "does_not_exist.py"
    good = tmp_path / "test_good.py"
    good.write_text(
        "\n".join(
            [
                "def test_r01_ok():",
                "    pass",
            ]
        ),
        encoding="utf-8",
    )

    # Act
    links = extract_links_from_paths([missing, good])

    # Assert: 読取不能はスキップし、正常ファイルは処理される
    assert links == {"R-01": ("test_good::test_r01_ok",)}


@pytest.mark.unit
@pytest.mark.requirement("R-48")
def test_undecodable_file_is_skipped(tmp_path: Path) -> None:
    """文字コードを解釈できないファイルはスキップする（R-48）。

    req: R-48
    """
    # Arrange: UTF-8 として不正なバイト列を書き込む
    bad = tmp_path / "test_bad.py"
    bad.write_bytes(b"\xff\xfe\x00 def test_r01(): pass")
    good = tmp_path / "test_good.py"
    good.write_text(
        "\n".join(
            [
                "def test_r02_ok():",
                "    pass",
            ]
        ),
        encoding="utf-8",
    )

    # Act
    links = extract_links_from_paths([bad, good])

    # Assert
    assert links == {"R-02": ("test_good::test_r02_ok",)}


@pytest.mark.unit
@pytest.mark.requirement("R-47")
def test_unparsable_file_in_paths_is_skipped(tmp_path: Path) -> None:
    """構文解析不能なファイルはスキップし他ファイルを処理する（R-47）。

    req: R-47
    """
    # Arrange
    broken = tmp_path / "test_broken.py"
    broken.write_text("def test_broken(:\n    pass", encoding="utf-8")
    good = tmp_path / "test_good.py"
    good.write_text("def test_r03_ok():\n    pass", encoding="utf-8")

    # Act
    links = extract_links_from_paths([broken, good])

    # Assert
    assert links == {"R-03": ("test_good::test_r03_ok",)}


@pytest.mark.unit
@pytest.mark.requirement("R-17")
def test_empty_paths_returns_empty_dict() -> None:
    """空のパス一覧では空dictを返す（R-17 の境界）。

    req: R-17
    """
    # Arrange / Act
    links = extract_links_from_paths([])

    # Assert
    assert links == {}
