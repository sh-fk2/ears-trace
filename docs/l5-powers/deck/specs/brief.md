# Brief

## Presentation Goal
ears-trace というツールが「EARS要件とテストのトレーサビリティ」を可視化し、テストの穴（未検証の要件）を機械的に検出することを、短く示す。Kiro University Challenge の Lesson 5(Powers) 実演として、ears-trace の自己トレース結果をスライド化する。

## Audience
開発者・レビュアー。EARS記法と自動テストの基礎知識あり。

## Format
3〜4枚の簡潔なデッキ。

## Tone & Style
技術的・簡潔・落ち着いたダークテーマ。

## Source Material (ears-trace 自己トレース結果)
- ears-trace は requirements.md(EARS)を解析し、要件ID(R-01形式)を抽出する。
- pytestのテストから3方式(マーカー/命名/docstring)で要件IDを拾い、要件↔テストを対応づける。
- 全要件を covered(テスト済み) と uncovered(穴) に排他かつ網羅に分割する。
- 自己トレース結果: 50要件中 覆われている割合は高く、未検証の穴を機械的に特定できる。
- 出力は自己完結HTML、CI向けのcheck(穴があり閾値未満なら非ゼロ終了)、未検証要件のpytestスタブ生成。
- Property-based testing(Hypothesis)で、集合分割・単調性・順序不変性・決定論性などの不変条件を検証している。

## Key Message
「要件を書いたら、テストの穴が自動で見える」。ears-trace は仕様駆動開発の次の一手を自動化する。
