# Requirements Document

（要件定義書: ears-trace）

## Introduction

ears-trace は、EARS 記法で書かれた要件文書を入力に、テストとのトレーサビリティを
可視化し、テストの抜け漏れ（未テストの要件＝穴）を明らかにする CLI ツールである。
要件を書いたものの、それぞれがテストで検証されているか把握できない、という課題を
解決する。要件文書とテスト群を突き合わせ、どの要件がテスト済みでどの要件が未検証か
を一覧化し、HTML レポート・CI 判定・未検証要件のテスト雛形生成を提供する。

本書は ears-trace が満たすべき機能要件を EARS 記法（Ubiquitous / Event(WHEN) /
State(WHILE) / Unwanted(IF-THEN) / Optional(WHERE)）で定義する。各要件には `R-01`
形式の識別子を付与し、テスト可能な粒度で受け入れ基準を記述する。

## Glossary

- **EARS**: Easy Approach to Requirements Syntax。要件を定型構文で書く記法。
- **要件行**: 大文字小文字を問わず述語として `SHALL` を含むテキスト行。ツールが要件として抽出する対象。ただしインラインコード（バッククォート内）にのみ現れる場合は要件行とみなさない。
- **明示 ID**: `R-01` のように `[A-Z]{1,5}-\d{1,4}` に一致する要件識別子。
- **採番 ID**: 明示 ID を持たない要件行に対し、衝突しないよう自動付与される `R-NN` 形式の ID。
- **トレースリンク**: ある要件 ID を充足するテスト（1件以上）の対応関係。
- **covered / uncovered**: テストが 1 件以上紐づく要件を covered、紐づかない要件を uncovered（穴）と呼ぶ。
- **カバレッジ率**: covered 要件数 ÷ 全要件数（0.0〜1.0）。要件が 0 件のときは 1.0 とみなす。
- **決定論的生成**: 同一入力に対して常に同一の出力を返す性質。

## Requirements

### 要件 1: EARS 要件のパースとパターン分類

**ユーザーストーリー:** 要件管理者として、requirements.md から EARS 要件を自動抽出しパターン分類したい。手作業での棚卸しをなくすためである。

#### 受け入れ基準

1. R-01: IF 入力テキストの行が大文字小文字を問わず `SHALL` を含む THEN THE SYSTEM SHALL その行を要件行として抽出する。ただし、インラインコード（バッククォートで囲まれた範囲）内にのみ `SHALL` が現れる行は、要件行として抽出しない
2. R-02: WHEN 要件行を分類する THE SYSTEM SHALL Ubiquitous / Event(WHEN) / State(WHILE) / Unwanted(IF-THEN) / Optional(WHERE) のいずれかのパターンに分類する
3. R-03: IF 要件行が `IF ... THEN ... SHALL` と `WHEN ... SHALL` の双方に一致し得る THEN THE SYSTEM SHALL Unwanted を Event より優先して分類する
4. R-04: IF 要件行が `WHERE`・`WHILE` 節と単なる `SHALL` の双方に一致し得る THEN THE SYSTEM SHALL Optional・State を Ubiquitous より優先して分類する
5. R-05: WHERE 要件行が 5 つの EARS パターンのいずれにも一致しない THE SYSTEM SHALL その要件を Unknown パターンとして分類する
6. R-06: IF 要件行が箇条書き記号（`-`・`*`・`+`）・番号（`1.`）・見出し（`#`）の接頭辞を持つ THEN THE SYSTEM SHALL 抽出前にそれらの接頭辞と前後空白を除去して原文を正規化する
7. R-07: WHERE 要件行が `[A-Z]{1,5}-\d{1,4}` 形式の明示 ID を含む THE SYSTEM SHALL その明示 ID を要件 ID として採用する
8. R-08: IF 要件行が明示 ID を含まない THEN THE SYSTEM SHALL 既存の明示 ID および採番済み ID と衝突しない `R-NN` 形式の ID を採番する
9. R-09: IF 同一の要件 ID が複数回出現する THEN THE SYSTEM SHALL 2 件目以降へ `-2`・`-3` の連番接尾辞を付与して要件 ID を一意化する
10. R-10: THE SYSTEM SHALL 抽出した要件を入力テキストの出現順で返す

### 要件 2: テストコードからのトレースリンク抽出

**ユーザーストーリー:** 開発者として、テストがどの要件を充足するかを複数の書き方で宣言したい。プロジェクトごとに異なるテスト記法へ柔軟に対応するためである。

#### 受け入れ基準

1. R-11: WHEN テスト関数に付与された `@pytest.mark.requirement("R-01")` 形式のマーカーを処理する THE SYSTEM SHALL その引数の要件 ID をテストと要件のリンクとして抽出する
2. R-12: WHEN `test_r01_...` の命名規約に一致するテスト関数名を処理する THE SYSTEM SHALL 関数名から要件 ID を抽出しリンクとして扱う
3. R-13: WHEN テスト関数の docstring に含まれる `req: R-01` 形式のタグを処理する THE SYSTEM SHALL そのタグの要件 ID をリンクとして抽出する
4. R-14: WHEN 抽出した要件 ID を照合する THE SYSTEM SHALL `r01` や `R1` などの表記を `R-01`（接頭辞大文字・番号 2 桁ゼロ埋め）に正規化する
5. R-15: WHERE 1 つのテストが複数の要件 ID を宣言し、または 1 つの要件に複数のテストが紐づく THE SYSTEM SHALL その多対多のリンクをすべて保持する
6. R-16: THE SYSTEM SHALL 各テストの識別子を `モジュール名::テスト関数名` 形式で生成する（クラス内テストメソッドは対象外とする）
7. R-17: WHEN 複数のテストファイルを処理する THE SYSTEM SHALL 全ファイルのリンクを要件 ID 単位で統合する
8. R-18: THE SYSTEM SHALL 要件に紐づくテスト ID を重複排除し整列した状態で返す

### 要件 3: カバレッジ集計（排他かつ網羅な分割）

**ユーザーストーリー:** 品質担当者として、全要件を「テスト済み」と「未テスト」に漏れなく重複なく分けたい。テストの穴を正確に把握するためである。

#### 受け入れ基準

1. R-19: WHEN 要件とトレースリンクからレポートを構築する THE SYSTEM SHALL すべての要件に対しトレースリンクを 1 件ずつ生成する
2. R-20: IF ある要件に紐づくテストが存在しない THEN THE SYSTEM SHALL その要件のトレースリンクを空のテスト集合（＝未充足）として生成する
3. R-21: THE SYSTEM SHALL テストが 1 件以上紐づく要件 ID の集合を covered として算出する
4. R-22: THE SYSTEM SHALL 全要件 ID から covered を除いた集合を uncovered（穴）として算出する
5. R-23: THE SYSTEM SHALL covered と uncovered が重複を持たず、かつ両者の和が全要件 ID に一致する分割を保証する
6. R-24: THE SYSTEM SHALL カバレッジ率を covered 要件数 ÷ 全要件数（0.0〜1.0）として算出する
7. R-25: IF 要件が 0 件である THEN THE SYSTEM SHALL カバレッジ率を 1.0 とみなす

### 要件 4: HTML トレーサビリティレポート生成

**ユーザーストーリー:** 利用者として、外部依存なしで開ける HTML レポートでトレーサビリティとカバレッジを確認したい。共有や証跡保存を容易にするためである。

#### 受け入れ基準

1. R-26: WHEN レポートを生成する THE SYSTEM SHALL 外部リソースに依存しない自己完結の静的 HTML（インライン CSS）を出力する
2. R-27: THE SYSTEM SHALL 全要件について ID・EARS パターン・要件原文・紐づくテスト・covered/gap 状態を列挙したトレーサビリティ表を出力する
3. R-28: THE SYSTEM SHALL covered 要件数 / 全要件数とカバレッジ率（百分率）をサマリとして出力する
4. R-29: THE SYSTEM SHALL 入力ファイル内容の SHA-256 ハッシュを HTML に埋め込む
5. R-30: THE SYSTEM SHALL 生成時刻を UTC の ISO 8601 形式で HTML に埋め込む
6. R-31: WHEN 要件原文やテスト ID を HTML に描画する THE SYSTEM SHALL HTML 特殊文字をエスケープして出力する

### 要件 5: pytest スタブの決定論的生成

**ユーザーストーリー:** 開発者として、未テスト要件に対応する pytest の雛形を自動生成したい。テストの書き始めを高速化するためである。

#### 受け入れ基準

1. R-32: WHEN スタブを生成する THE SYSTEM SHALL uncovered（未テスト）要件に対応する pytest 雛形のみを生成する
2. R-33: THE SYSTEM SHALL 各スタブに `@pytest.mark.requirement("R-NN")` マーカーと `req: R-NN` タグを付与し、生成物が自ツールで再リンク可能な形式にする
3. R-34: THE SYSTEM SHALL 未テスト要件を入力の出現順に従ってスタブ化する
4. R-35: WHEN 同一の入力に対して繰り返しスタブを生成する THE SYSTEM SHALL 常に同一の出力を返す（決定論的・冪等）
5. R-36: IF 未テスト要件が 1 件も存在しない THEN THE SYSTEM SHALL ヘッダのみを含むスタブモジュールを出力する

### 要件 6: CLI（report / check / generate）

**ユーザーストーリー:** 利用者として、単一の CLI からレポート出力・CI 判定・スタブ生成を実行したい。用途に応じて使い分けるためである。

#### 受け入れ基準

1. R-37: THE SYSTEM SHALL `report`・`check`・`generate` の 3 サブコマンドを提供する
2. R-38: WHEN サブコマンドが指定されずに起動される THE SYSTEM SHALL エラーとしてサブコマンド必須である旨を返す
3. R-39: WHEN `report` が実行される THE SYSTEM SHALL HTML レポートを既定 `out/traceability.html`（`-o/--output` で変更可能）へ書き出し終了コード 0 を返す
4. R-40: WHERE `--tests` にテストディレクトリが指定される THE SYSTEM SHALL その配下の `test_*.py` を再帰的に収集してリンク抽出に用いる
5. R-41: WHEN `check` が実行され、uncovered 要件が存在し、かつカバレッジ率が `--min-coverage`（既定 1.0）を下回る THE SYSTEM SHALL 非ゼロ終了コード（1）を返す
6. R-42: IF `check` 実行時に uncovered 要件が無い、またはカバレッジ率が閾値以上である THEN THE SYSTEM SHALL 終了コード 0 を返す
7. R-43: WHEN `generate` が実行される THE SYSTEM SHALL スタブを既定 `tests/test_generated_stubs.py`（`-o/--output` で変更可能）へ書き出し終了コード 0 を返す
8. R-44: WHEN `report` または `generate` が出力先を書き込む THE SYSTEM SHALL 出力先の親ディレクトリが無ければ作成する

### 要件 7: 頑健性（クラッシュしない）

**ユーザーストーリー:** 利用者として、空入力や壊れた入力でもツールが落ちないことを求める。CI や日常運用で安全に使うためである。

#### 受け入れ基準

1. R-45: IF 入力テキストが空である THEN THE SYSTEM SHALL エラーで停止せず空の要件集合を返す
2. R-46: IF 入力に `SHALL` を含む要件行が 1 件も無い THEN THE SYSTEM SHALL エラーで停止せず空の要件集合を返す
3. R-47: IF テストファイルが構文的に解析できない THEN THE SYSTEM SHALL そのファイルをスキップし、処理を中断せず継続する
4. R-48: IF テストファイルが読み取れない、または文字コードを解釈できない THEN THE SYSTEM SHALL そのファイルをスキップし、処理を中断せず継続する
5. R-49: IF `--tests` に存在しないディレクトリが指定される THEN THE SYSTEM SHALL エラーで停止せず、テスト無し（全要件 uncovered）として処理する
6. R-50: WHERE `--enrich` によるEARSパターンの説明補足が有効であり IF 外部からの説明取得が失敗または利用不可である THEN THE SYSTEM SHALL 処理を中断せず内蔵の既定説明にフォールバックする
