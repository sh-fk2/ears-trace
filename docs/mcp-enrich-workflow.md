# MCP連携（L6）: fetch MCPでEARS注釈を取得しレポートに反映する

ears-trace は実行時に、EARSパターンの説明注釈をレポートへ併記できる（`report --enrich`）。
注釈の取得元として **Kiro の MCP（fetch サーバ）** を使うのが L6 の連携ポイント。

## アーキテクチャ（なぜこの形か）

MCPサーバを呼ぶのは **Kiro（エージェント）** であり、Python プロセスではない。
そこで責務を分離する:

```
[Kiro + fetch MCP]                         [ears-trace (Python)]
公式EARSガイドをWeb取得         →  注釈JSON  →  report --enrich で読み込み
(mcp.jsonのfetchサーバを使用)      (annotations.json)   レポートに説明を併記
```

- **Kiro 側**: `.kiro/settings/mcp.json` の `fetch` サーバでEARS解説ページを取得し、
  パターン値→説明文の JSON（`annotations.json`）として保存する。
- **ears-trace 側**: `--enrich annotations.json` でその JSON を読み、レポートに併記する。
  JSONが無い/壊れている場合は内蔵の既定説明にフォールバックし停止しない（R-50 頑健性）。

この分離により「Pythonが直接ネットワークを叩かない（安全）」「MCP取得結果が
プロダクト出力に組み込まれる（L6の証跡が明確）」を両立する。

## MCP サーバ定義（単一ソース）

`.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"],
      "disabled": false,
      "autoApprove": ["fetch"]
    }
  }
}
```

## 手順（デモで見せる流れ）

1. Kiro（IDE/CLI）で fetch MCP を使い、EARS公式ガイドのURLを取得させる。
   例: 「fetch MCPで https://... のEARS解説を取得し、各パターンの説明を
   {\"UBIQUITOUS\": \"...\", \"EVENT\": \"...\"} 形式のJSONで out/annotations.json に保存して」
2. ears-trace を `--enrich` 付きで実行:

   ```bash
   ears-trace report \
     --requirements .kiro/specs/ears-trace/requirements.md \
     --tests tests/ \
     -o out/traceability.html \
     --enrich out/annotations.json
   ```

3. 生成HTMLの各要件行に、MCPで取得したパターン説明が併記される。

## 注釈JSONの形式

キーは `EarsPattern` の値（大文字）、値は説明文。

```json
{
  "UBIQUITOUS": "常時成立する普遍的要件の説明",
  "EVENT": "トリガに応答する要件の説明",
  "STATE": "...",
  "UNWANTED": "...",
  "OPTIONAL": "..."
}
```

部分的な定義でもよい（未定義パターンは内蔵既定説明にフォールバック）。
