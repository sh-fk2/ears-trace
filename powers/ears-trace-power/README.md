# ears-trace power (Bonus2)

ears-trace を Kiro power としてパッケージ化したもの（Kiro University Challenge の Bonus2）。

## 構成

```
ears-trace-power/
├── plugin.json          # 必須マニフェスト（name/version/description/keywords 等）
├── skills/
│   └── trace/
│       └── SKILL.md     # ears-trace CLI の使い方を教えるスキル
└── README.md            # このファイル
```

## これは何か

Kiro power は、関連するツール・スキル・ベストプラクティスを束ねて、キーワードで
オンデマンドにロードさせる仕組み。この power は **ears-trace CLI の使い方（スキル）**を
束ねており、「要件のテスト漏れを調べて」等のキーワードで起動する。

- `plugin.json` の `keywords`（ears / requirements / traceability / テスト 等）が
  起動のトリガになる。
- `skills/trace/SKILL.md` が、ears-trace の3サブコマンド（report / check / generate）と
  テストリンクの書き方を教える。

## MCPサーバを持たない理由

ears-trace は純粋なCLIツールであり、外部サーバを必要としない。したがってこの power は
**plugin.json + skill の最小構成**でパッケージした（MCPサーバは同梱しない）。

## 公開

power は特別な承認なしに公開GitHubリポジトリとして共有できる。将来的に、キュレーション
済みの Kiro powers レジストリへのレビュー提出も任意で可能。

## 利用方法

1. この power をインストール（または powers ディレクトリに配置）する。
2. `ears-trace` CLI をインストールする（`pip install -e .` など）。
3. 要件のテスト漏れに関する依頼をすると、skill がロードされ CLI の使い方が提示される。
