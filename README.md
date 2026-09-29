# ears-trace

EARS記法で書かれた要件（`requirements.md`）を起点に、テストの抜け漏れを機械的に可視化するPython CLIツール。

仕様駆動開発（Spec-driven development）の「次の一手」を自動化する。要件を書いたら、どの要件にテストが紐づいていて、どの要件が**テストされていない穴**なのかを、トレーサビリティ表として一目で分かるようにする。

## できること

1. **トレーサビリティ表の生成** — 要件ID ↔ テスト の対応を静的HTMLレポートで可視化
2. **カバレッジ照合** — テストが紐づいていない要件（穴）を検出（CIで失敗させることも可能）
3. **pytestスタブ生成** — 未充足要件に対応するテスト雛形を自動生成

## インストール

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 使い方

```bash
# HTMLトレーサビリティレポートを生成
ears-trace report examples/sample_requirements.md --tests tests/ -o out/traceability.html

# カバレッジを判定（穴があり閾値未満なら非ゼロ終了・CI向け）
ears-trace check examples/sample_requirements.md --tests tests/ --min-coverage 0.8

# 未充足要件のpytestスタブを生成
ears-trace generate examples/sample_requirements.md --tests tests/ -o tests/test_generated_stubs.py
```

## テストと要件のリンク方法

pytest 側で、次のいずれかの方法で要件IDを宣言する。

```python
import pytest

# 1. マーカー
@pytest.mark.requirement("R-02")
def test_invalid_form_shows_errors() -> None:
    ...

# 2. 命名規約（test_r02_... -> R-02）
def test_r02_invalid_form() -> None:
    ...

# 3. docstring内のタグ
def test_something() -> None:
    """req: R-02"""
    ...
```

## EARSパターン

| パターン | 構文 |
|---|---|
| Ubiquitous | `THE SYSTEM SHALL <応答>` |
| Event | `WHEN <トリガ> THE SYSTEM SHALL <応答>` |
| State | `WHILE <状態> THE SYSTEM SHALL <応答>` |
| Unwanted | `IF <条件> THEN THE SYSTEM SHALL <応答>` |
| Optional | `WHERE <機能> THE SYSTEM SHALL <応答>` |

## 開発

```bash
pytest --cov=src/ears_trace --cov-report=term-missing
ruff check .
```
