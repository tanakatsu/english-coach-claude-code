# Architecture: English Coach

## Overview
Stop hook → ローカルサーバー → ダッシュボード

## Data Flow
1. Stop hook
2. JSONL解析
3. 差分検出
4. 補正 or サマリー
5. サーバー送信
6. UI表示

## Input Source
~/.claude/projects/<project>/<session>.jsonl

## Language Detection
UnicodeでJP/EN判定

## API
- POST /api/feedback
- POST /api/summary
- GET /api/latest
- GET /api/history

## Storage
SQLite history.db

## Dashboard
2秒ポーリング

## Critical Points
- JSONLパース
- 言語判定
- 非ブロッキング

## Error Handling
すべて非ブロッキング

## Extensibility
- SRS
- 通知
- モデル変更
