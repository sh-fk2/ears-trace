---
inclusion: always
---

# EARS パターンの語彙と判定規約

## 規約

ears-trace が扱う EARS（Easy Approach to Requirements Syntax）は次の5パターン + 未分類とする。
コード内でパターンを表現するときは、必ずこの列挙値・この判定順序に従う。

| パターン | 列挙値 | 構文 |
|---|---|---|
| Ubiquitous | `UBIQUITOUS` | `THE SYSTEM SHALL <応答>` |
| Event | `EVENT` | `WHEN <トリガ> THE SYSTEM SHALL <応答>` |
| State | `STATE` | `WHILE <状態> THE SYSTEM SHALL <応答>` |
| Unwanted | `UNWANTED` | `IF <条件> THEN THE SYSTEM SHALL <応答>` |
| Optional | `OPTIONAL` | `WHERE <機能> THE SYSTEM SHALL <応答>` |
| （未分類） | `UNKNOWN` | いずれにも該当しない |

**判定順序（重要）**: 上位の複合パターンを単純パターンより先に評価する。
`UNWANTED → EVENT → STATE → OPTIONAL → UBIQUITOUS`、いずれも該当しなければ `UNKNOWN`。

- `SHALL` の検出は大文字小文字を区別しない。
- パターン名・列挙値は上表の綴りで統一する（`Optional` を `OPT` などと略さない）。

## 意図（なぜこの規約か）

- **判定順序を固定しないと分類がブレる**。`IF ... THEN ... SHALL` は `WHEN ... SHALL`
  にも部分一致しうるため、Unwanted を Event より先に評価しないと誤分類する。同様に
  `WHERE`/`WHILE` を単なる `SHALL`（Ubiquitous）より先に見ないと、複合節が握りつぶされる。
- 列挙値の綴りを統一するのは、`@pytest.mark.requirement` やレポート表示・ドッグフーディング
  （ears-trace 自身の要件を ears-trace で解析する）で表記揺れが致命的になるため。
- requirements.md の R-02〜R-05 と一致させ、spec と実装の乖離を防ぐ。

## コード例

```python
# 良い例: 複合パターンを先に評価する判定順（この順序を守る）
_PATTERN_ORDER = (
    (EarsPattern.UNWANTED, r"\bIF\b.+\bTHEN\b.+\bSHALL\b"),
    (EarsPattern.EVENT, r"\bWHEN\b.+\bSHALL\b"),
    (EarsPattern.STATE, r"\bWHILE\b.+\bSHALL\b"),
    (EarsPattern.OPTIONAL, r"\bWHERE\b.+\bSHALL\b"),
    (EarsPattern.UBIQUITOUS, r"\bSHALL\b"),
)

# 悪い例: Ubiquitous(SHALL)を先に見てしまうと WHEN/IF 節が全部 Ubiquitous に潰れる
# for pattern in [UBIQUITOUS, EVENT, ...]  # ← 順序が逆。禁止
```
