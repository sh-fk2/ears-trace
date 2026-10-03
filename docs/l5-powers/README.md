# L5 Powers: Kiro power でカバレッジ説明デッキを生成

Lesson 5（Powers）の実演。既存の Kiro power **`sample-spec-driven-presentation-maker`**
（spec駆動のPowerPoint生成）を使い、ears-trace の価値と自己トレース結果を説明する
スライドデッキを生成した。

## 使った power

- **名前**: `sample-spec-driven-presentation-maker`
- **種別**: 既存（インストール済み）の Kiro power。MCPサーバ `sdpm` と
  スキル（sdpm-spec / sdpm-style / sdpm-translate / sdpm-vibe）を同梱。
- **ロード契機**: 「スライド」「プレゼン」等のキーワードで power が自動的に候補化され、
  ツール（`start_presentation` 他）がオンデマンドでロードされる。

## ears-trace との噛み合わせ（後付けでない接続）

ears-trace が検出した「テストの穴」や自己トレース結果という**プロジェクト固有の素材**を、
power に渡してスライド化した。ツール（ears-trace）の出力を power がプレゼン資産に変換する、
という機能的な連携になっている。

- 役割分担: L5=既存powerの再利用 / L7=自作の限定権限エージェント / Bonus2=自作power。

## 実際に呼んだ power のツール（証跡）

1. `start_presentation(mode="vibe")` — 高速生成モードの起動
2. `init_presentation(name="ears-trace-coverage")` — デッキ初期化
3. `run_python(...)` — brief.md / outline.md / deck.json / slides/*.json の作成
4. `list_styles()` / `apply_style(style="elegant-dark")` — スタイル適用
5. `list_templates()` — テンプレート確認（blank-dark）
6. `start_presentation(mode="composer")` + `read_workflows(...)` — スライド合成
7. `generate_pptx(deck_id=...)` — PPTX生成（4枚）

## 成果物

- `ears-trace-coverage.pptx` — 生成された4枚のデッキ（title / how-it-works / self-trace / quality）
- `deck/` — power のワークスペース（deck.json / slides / specs）をコピーしたもの

## デッキ構成（outline）

1. **title** — ears-trace とは。「要件→テストの穴を自動可視化」という価値
2. **how-it-works** — パース→テスト照合→カバレッジ分割→出力の流れ
3. **self-trace** — ツールが自分の要件をトレースし穴を機械的に見つける（ドッグフーディング）
4. **quality** — PBT(Hypothesis)で不変条件を検証し正しさを担保

## 備考

- power の出力は既定で `~/Documents/SDPM-Presentations/` に生成される。
  本リポジトリにはL5の証跡として成果物をコピーして収めた。
- 生成時の警告（top-heavy=上寄り）は軽微なレイアウトバランスの指摘で、内容に影響しない。


## デモ動画用のレッスン表紙カード（lesson-cards.pptx）

同じ power（spec-driven-presentation-maker, elegant-dark）で、デモ動画の各レッスン
区切りに挟む**表紙カード9枚**も生成した。各カードは「レッスン番号 / 名前 /
このプロジェクトでの一言」で構成し、動画視聴者が L1→L2→… と追えるようにする。

- `lesson-cards.pptx` — 9枚（L1〜L7 + Bonus2 + Bonus1）
- `lesson-cards/` — 生成に使った slides JSON と outline

これも power を実用に使った証跡（L5）であり、デモ動画の構成素材でもある。
