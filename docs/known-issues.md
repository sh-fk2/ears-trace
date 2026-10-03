# 既知の問題（Known Issues）

## KI-01: Glossary等の説明文を要件行として誤検出する

### 概要
自己トレース実行時、requirements.md の **Glossary セクションの説明文**が
要件行として誤抽出され、幻の要件 `R-51` が採番される。

### 再現
```bash
ears-trace report --requirements .kiro/specs/ears-trace/requirements.md --tests tests/ -o out/self-trace.html
# -> 要件が51件検出される（本来はR-01〜R-50の50件）
# -> R-51 の原文が Glossary の「要件行: ... を含むテキスト行」になっている
```

### 原因
パーサは「`SHALL`（大文字小文字問わず）を含む行」を要件行とみなす（R-01）。
Glossary の用語説明の中に、説明目的で `SHALL` という語が登場する行があり、
これが本来の EARS 要件ではないのに要件として抽出されてしまう。

該当行（requirements.md の Glossary）:
- 「要件行」の定義文。この語の説明として判定語を含むため誤検出される。

### 影響
- 自己トレースで要件数が実際より1件多く出る（51件）。
- その幻の要件が唯一の「穴（uncovered）」として表示され、カバレッジが 98% になる。
- 実害は自己ドッグフーディング時の表示のみ。通常の利用（純粋なEARS要件文書）では
  Glossary のような説明文が無ければ発生しない。

### 分類
パーサの抽出範囲の仕様の穴。見出し直下の説明文・コードブロック内・引用内・
用語定義などの「要件ではない SHALL 行」を要件抽出から除外する必要がある。

### 対処方針（別タスクで扱う）
spec 駆動を保つため、requirements.md / design.md に抽出範囲の仕様を追記し、
TDD（誤検出を再現する失敗テスト → パーサ改善 → 緑）で修正する。
L5（Powers）完了後に独立タスクとして対応する。

### ステータス
- 発見: L5（Powers）作業中の自己トレースで検出
- 対応: **解決済み（CLOSED）**

### 解決内容
パーサに「インラインコード（バッククォート内）を除去してから `SHALL` を判定する」
処理を追加（`parser._strip_inline_code`）。これにより Glossary の `` `SHALL` ``
のようなコード表記の引用を要件行として誤検出しなくなった。
- spec更新: requirements.md R-01 に除外規約を追記、design.md parse節に反映
- TDD: KI-01 再現テスト3件（インラインコードのみのSHALL除外／述語SHALL維持／
  Glossary混在で幻要件が出ない）を追加し RED→GREEN
- 検証: 自己トレースが 50/50（100%）になり、幻の R-51 が消滅
- 併せて requirements.md の Glossary 定義文を単一バッククォート表記に修正
