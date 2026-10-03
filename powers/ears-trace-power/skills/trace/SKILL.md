---
name: ears-trace
description: >-
  EARS記法で書かれた要件(requirements.md)とpytestのテストを突き合わせ、
  テストの穴(未検証の要件)を検出するとき。要件のトレーサビリティ表(HTML)を作る、
  テストカバレッジをCIで判定する、未検証要件のpytestスタブを生成する、といった用途。
  「要件のテスト漏れを調べて」「EARS要件とテストの対応を可視化して」
  「どの要件がテストされていないか」などで起動する。
  Trace EARS requirements against pytest tests, detect untested requirements,
  and generate an HTML traceability report, CI coverage check, or pytest stubs.
---

# ears-trace

EARS要件とテストのトレーサビリティを可視化するCLIツール `ears-trace` を使う。

## 前提

`ears-trace` がインストールされていること。未インストールなら:

```bash
pip install ears-trace    # もしくはリポジトリで: pip install -e .
```

## 3つのサブコマンド

### 1. report — HTMLトレーサビリティレポートを生成

要件ごとに「どのテストが紐づくか」「テスト済み(covered)か穴(gap)か」を表にする。

```bash
ears-trace report --requirements <requirements.md> --tests <tests_dir> -o out/traceability.html
```

- `--enrich <annotations.json>` を付けると、各EARSパターンの説明を併記する
  （MCP(fetch)で取得した注釈JSONを渡す運用）。

### 2. check — カバレッジをCIで判定

穴があり、かつカバレッジ率が閾値未満なら非ゼロ終了する。CIに組み込む。

```bash
ears-trace check --requirements <requirements.md> --tests <tests_dir> --min-coverage 0.8
```

### 3. generate — 未検証要件のpytestスタブを生成

テストが無い要件に対応するpytest雛形を出力する。

```bash
ears-trace generate --requirements <requirements.md> --tests <tests_dir> -o tests/test_generated_stubs.py
```

## テストと要件のリンク方法

pytest側で、次のいずれかで要件IDを宣言するとtraceが拾う。

```python
import pytest

@pytest.mark.requirement("R-02")      # 1. マーカー
def test_a() -> None: ...

def test_r02_b() -> None: ...          # 2. 命名規約 test_r02_... -> R-02

def test_c() -> None:
    """req: R-02"""                    # 3. docstringタグ
```

## 典型フロー

1. 要件を書く / 既存の requirements.md を用意する
2. `ears-trace report` でトレーサビリティ表を見て、穴を把握する
3. `ears-trace generate` で穴のスタブを出し、テストを書く
4. `ears-trace check` をCIに入れ、カバレッジ閾値を守る

MCPサーバは不要。純粋なCLIツールとして動作する。
