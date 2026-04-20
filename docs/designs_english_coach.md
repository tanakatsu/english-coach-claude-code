# English Learning Sidebar for Claude Code

## Problem
日々の開発中、日本語話者エンジニアは日本語と英語を行き来しているが、
英語学習は実務と切り離され継続しにくい。

## Value Proposition
既に書いている文を学習素材にする。
- 日本語 → 自然な技術英語
- 英語 → より自然な表現
リアルタイム補正 + セッション後サマリー

## Scope
### In Scope
- Stop hook
- メッセージ検出
- JP/EN判定
- ダッシュボード表示
- サマリー生成

### Out of Scope
- SRS
- クラウド同期
- モバイル対応

## Constraints
- macOSローカル環境
- 非侵入
- 3秒以内応答

## High-Level Approach
Stop hook → メッセージ検出 → 補正 → ローカル表示

## Success Criteria
- 3秒以内表示
- 履歴確認可能
- パターン分析可能
