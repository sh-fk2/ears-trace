# ears-trace

[English README](./README.md)

EARS記法で書かれた要件（`requirements.md`）を起点に、テストの抜け漏れを機械的に可視化するPython CLIツール。

仕様駆動開発（Spec-driven development）の「次の一手」を自動化する。要件を書いたら、どの要件にテストが紐づいていて、どの要件が**テストされていない穴**なのかを、トレーサビリティ表として一目で分かるようにする。

**Kiro University Challenge** の最終プロジェクトとして、7レッスン全部＋ボーナスを実演する形で作成した。

## デモ動画

[![Demo video](https://img.youtube.com/vi/ZZ62xMf4aig/0.jpg)](https://youtu.be/ZZ62xMf4aig)

3分のデモ動画: https://youtu.be/ZZ62xMf4aig

## できること

1. **トレーサビリティ表の生成** — 要件ID ↔ テスト の対応を自己完結の静的HTMLレポートで可視化
2. **カバレッジ照合** — テストが紐づいていない要件（穴）を検出（CIで失敗させることも可能）
3. **pytestスタブ生成** — 未検証要件に対応するテスト雛形を自動生成

## インストール

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 使い方

```bash
# HTMLトレーサビリティレポートを生成
ears-trace report --requirements .kiro/specs/ears-trace/requirements.md --tests tests/ -o out/traceability.html

# カバレッジを判定（穴があり閾値未満なら非ゼロ終了・CI向け）
ears-trace check --requirements .kiro/specs/ears-trace/requirements.md --tests tests/ --min-coverage 0.8

# 未検証要件のpytestスタブを生成
ears-trace generate --requirements .kiro/specs/ears-trace/requirements.md --tests tests/ -o tests/test_generated_stubs.py

# 任意: MCP(fetch)で取得したEARSパターン注釈をレポートに併記（docs/mcp-enrich-workflow.md 参照）
ears-trace report --requirements <req.md> --tests tests/ -o out/traceability.html --enrich out/annotations.json
```

## テストと要件のリンク方法

pytest 側で、次のいずれかの方法で要件IDを宣言する。

```python
import pytest


# 1. マーカー
@pytest.mark.requirement("R-02")
def test_invalid_form_shows_errors() -> None: ...


# 2. 命名規約（test_r02_... -> R-02）
def test_r02_invalid_form() -> None: ...


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
pytest --cov=src/ears_trace --cov-report=term-missing   # 175テスト・カバレッジ99%
ruff check .
```

## Kiro University Challenge — 各レッスンの組み込み

本プロジェクトは Kiro を主要開発ツールとして構築した。`.kiro/` フォルダに各レッスンの証跡がある。

| レッスン | 機能 | リポジトリ内の場所 |
|---|---|---|
| **L1 仕様駆動開発** | 要件→設計→タスクのspec | `.kiro/specs/ears-trace/{requirements,design,tasks}.md` — ツール自身の要件をEARSで記述（ドッグフーディング）。Kiro IDE の Spec モードで作成 |
| **L2 Steering** | プロジェクトの永続知識 | `.kiro/steering/{ears-vocabulary,report-format,python-conventions}.md` — コード生成を制御する規約 |
| **L3 Hooks** | イベント駆動の自動化 | `.kiro/hooks/{retrace-on-save,lint-on-save}.json` — 要件保存時に再トレース／Python保存時にRuff |
| **L4 プロパティベーステスト**（IDE限定） | specからHypothesis PBT | `tests/test_properties_*.py` — プロパティP1〜P7（集合分割・単調性・決定論性・パーサ頑健性ほか）。各テストに要件IDを付与。Kiro IDE で実行 |
| **L5 Powers** | 既存powerの再利用 | `docs/l5-powers/` — `spec-driven-presentation-maker` power でカバレッジ結果をスライド化 |
| **L6 MCP** | 実行時に外部MCPを使う | `.kiro/settings/mcp.json`(fetch) + `src/ears_trace/enrich.py` — `--enrich` でMCP取得の注釈を併記。`docs/mcp-enrich-workflow.md` 参照 |
| **L7 カスタムエージェント** | 限定権限の専用エージェント | `.kiro/agents/requirements-reviewer.json` — 読み取り専用（read/glob/grepのみ、write除外、shellは`ears-trace`限定） |
| **Bonus2 自作power** | 自分でpowerを作る | `powers/ears-trace-power/` — plugin.json + skill で ears-trace 自身をパッケージ |
| **Bonus1 クラウドセッション** | Kiro Web / cloud config | ローカルの `.kiro` 設定を同期したクラウドセッションでビルド（テスト＋自己トレース）を実行 |

### ドッグフーディング

ears-trace は**自分自身の要件**をトレースできる。`ears-trace report --requirements .kiro/specs/ears-trace/requirements.md --tests tests/` を実行すると自己カバレッジ 50/50（100%）になる。この過程で見つかったパーサのエッジケース（インラインコード `` `SHALL` `` の誤検出）は `docs/known-issues.md`（KI-01）に記録し、修正済み。

## ライセンス

MIT
