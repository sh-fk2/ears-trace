---
inclusion: fileMatch
fileMatchPattern: "**/*.py"
---

# Python 実装規約（ears-trace 固有）

## 規約

### 純粋関数中心・副作用の隔離
- ドメインロジック（パース・リンク抽出・集計・レンダリング・スタブ生成）は
  **副作用のない純粋関数**として実装する。
- ファイルI/O・標準出力・終了コード・引数解析などの**副作用は CLI 層（cli.py）に集約**する。
- 非決定要素（現在時刻など）は**引数で注入可能**にする（例: `now: datetime | None = None`）。

### 不変データ
- 要件・トレースリンク・カバレッジ結果は `@dataclass(frozen=True)` で表現する。
- 集合は `frozenset`、系列は `tuple` を使い、破壊的変更を避ける。

### 頑健性（クラッシュしない）
- 外部入力（要件文書・テストファイル・外部取得）は境界で防御し、
  想定外でも**例外で停止せず**、空結果やスキップで継続する。
- 解析・読み取りで起こりうる例外はその場で捕捉し、呼び出し側へ伝播させない。

### スタイル
- PEP 8 に従い、すべての関数シグネチャに**型アノテーション**を付ける。
- lint/format は **Ruff** を使う（line-length=100, select=E,F,I,UP,B）。

## 意図（なぜこの規約か）

- **純粋関数にするのは PBT のため**。副作用がなければ Hypothesis で大量の生成入力を
  安全に流せる。決定論プロパティ（同一入力→同一出力）も純粋性が前提になる。
- 時刻を注入可能にするのは、生成時刻を固定してレポート/スタブの決定論性をテストするため。
- 不変データにするのは、順序不変性・冪等性のプロパティが偶発的な破壊で壊れないようにするため。
  また frozen なら要件の並び替え等でも元データが汚染されない。
- 頑健性を既定にするのは、CI や日常運用でツールが落ちると信頼を失うため（requirements.md 要件7）。

## コード例

```python
# 良い例: 純粋関数 + 時刻注入 + 不変な戻り値
from datetime import datetime, timezone


def build_report(
    requirements: tuple[Requirement, ...],
    links: dict[str, tuple[str, ...]],
    *,
    input_text: str,
    now: datetime | None = None,  # 非決定要素を注入可能に
) -> CoverageReport:  # frozen dataclass を返す（不変）
    generated = (now or datetime.now(timezone.utc)).isoformat()
    ...


# 良い例: 境界で防御し例外を伝播させない
def extract_links_from_source(source: str) -> dict[str, tuple[str, ...]]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}  # 解析不能はスキップ（クラッシュしない）


# 悪い例: ドメイン層でファイルを直接読む（副作用がドメインに漏れる）
def parse_file(path: str):  # ← 禁止。I/O は cli 層に置く
    text = open(path).read()
    ...
```
