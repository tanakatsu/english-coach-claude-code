# English Coach for Claude Code — v1 実装計画

## Context

`docs/designs_english_coach.md` と `docs/architecture_english_coach.md` に示された「Claude Code の対話中に発した日本語/英語メッセージを学習素材化するサイドバー」を v1 として実装する。現状リポジトリは設計ドキュメントと `.claude/` の安全フックのみで、アプリ本体のコードは未着手。

解決したい課題は「日本語話者エンジニアは日々英語と日本語を行き来しているのに、英語学習は実務と切り離されてしまう」こと。既にユーザーが Claude Code に向かって書いた自然文を素材に、リアルタイム補正とセッション後サマリーを非侵入的に提供する。v1 の成功基準は以下3点（設計書より）:

- Stop hook 完了から 3 秒以内にダッシュボードへ補正が表示される
- 履歴がいつでも確認できる
- セッションサマリーでパターン分析ができる

`TODOS.md` に「DB スキーマは SRS 拡張を壊さない設計にしておく」「launchd による常駐化は v2」と明記されているため、v1 では SRS/launchd を実装しないが **スキーマは v2 を阻害しない形** で切る。

確定した技術選定（会話で合意）:
- LLM: Anthropic Claude API（`claude-haiku-4-5-20251001`）
- サーバー: FastAPI + uvicorn
- UI: Vanilla HTML + JS（FastAPI から静的配信）
- 差分検出: 「前回処理済み UUID 以降の新規ユーザーメッセージだけを拾う」方式
- パッケージ管理: **uv**（`pyproject.toml` + `uv.lock`）

## Deliverables（ディレクトリ構成）

```
pyproject.toml               # uv で管理（fastapi, uvicorn, anthropic, python-dotenv, httpx）
uv.lock                      # uv が生成・コミット
.python-version              # uv が推奨する Python 固定
server.py                    # FastAPI サーバー（エントリ、`uv run python server.py`）
english_coach/
  __init__.py
  hook.py                    # Stop hook 本体（`uv run python -m english_coach.hook`）
  jsonl_reader.py            # JSONL パース + 前回処理 UUID 以降の抽出
  language.py                # Unicode ベースで JP/EN 判定
  corrector.py               # Claude API 呼び出し（補正 + サマリー）
  db.py                      # SQLite 初期化・CRUD
  config.py                  # パス/モデル名/APIキー等の集中管理
static/
  index.html                 # ダッシュボード（単一ファイル）
data/
  history.db                 # SQLite（初回起動時に自動作成、.gitignore）
.claude/settings.json        # Stop hook 登録（既存を編集）
.env.example                 # ANTHROPIC_API_KEY のテンプレート
README.md                    # 起動手順（v1のみ、短く）
```

**パッケージ管理は uv** を使用（`requirements.txt` ではなく `pyproject.toml` + `uv.lock`）。初期化は `uv init`、依存追加は `uv add fastapi uvicorn anthropic python-dotenv httpx`。実行は `uv run ...` で統一する。

## アーキテクチャ（データフロー）

```
Claude Code Stop イベント
  └─> .claude/settings.json の Stop hook
        └─> uv run python -m english_coach.hook  （stdin で session 情報受領）
              ├─ jsonl_reader: ~/.claude/projects/<proj>/<session>.jsonl を末尾走査
              │     ├─ SQLite の last_processed_uuid(session_id) 以降のみ抽出
              │     └─ `type=user` かつ `isMeta!=true` かつ
              │         `<command-*>`/`<local-command-*>` でないテキストのみ採用
              ├─ language: Unicode で JP/EN 判定（混在は「多数派」）
              ├─ corrector: 非同期で Claude API 呼び出し
              │     ├─ JP → 自然な技術英語
              │     └─ EN → より自然な英語（元が自然ならそのまま返す）
              ├─ POST http://127.0.0.1:8765/api/feedback  （1メッセージ=1POST）
              └─ last_processed_uuid を更新

FastAPI (127.0.0.1:8765)
  ├─ POST /api/feedback   → corrections テーブルに INSERT
  ├─ POST /api/summary    → summaries テーブルに INSERT（将来用、v1ではhookからは呼ばない）
  ├─ GET  /api/latest     → 直近 N 件（既定20）
  ├─ GET  /api/history    → ?session_id= ?limit= ?offset= でページング
  └─ GET  /              → static/index.html

Dashboard (index.html)
  └─ 2秒ごとに fetch('/api/latest') → 最新補正を先頭に追加表示
```

## DB スキーマ（v2 を阻害しない設計）

`TODOS.md` の指摘どおり、v1 では使わないが `pattern_id` を NULL 可で予約し、`session_date` を `ts` と別に持つ。

```sql
CREATE TABLE IF NOT EXISTS corrections (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  ts            TEXT    NOT NULL,           -- ISO8601, UTC
  session_id    TEXT    NOT NULL,
  session_date  TEXT    NOT NULL,           -- YYYY-MM-DD (ローカル), SRS集計用
  language      TEXT    NOT NULL CHECK(language IN ('ja','en')),
  original      TEXT    NOT NULL,
  correction    TEXT    NOT NULL,
  explanation   TEXT,                       -- なぜ直したか（短文）
  pattern_id    INTEGER,                    -- v2 の patterns テーブルへの FK（v1 は常に NULL）
  uuid          TEXT    NOT NULL UNIQUE     -- JSONL の message uuid（冪等性担保）
);
CREATE INDEX idx_corrections_session ON corrections(session_id);
CREATE INDEX idx_corrections_date    ON corrections(session_date);

CREATE TABLE IF NOT EXISTS summaries (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL UNIQUE,
  ts         TEXT NOT NULL,
  body       TEXT NOT NULL                  -- Markdown
);

CREATE TABLE IF NOT EXISTS hook_state (
  session_id          TEXT PRIMARY KEY,
  last_processed_uuid TEXT NOT NULL,
  updated_at          TEXT NOT NULL
);

-- v2 予約（空テーブルだけ作っておく）
CREATE TABLE IF NOT EXISTS patterns (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  signature    TEXT NOT NULL UNIQUE,
  description  TEXT,
  first_seen   TEXT NOT NULL,
  last_seen    TEXT NOT NULL,
  occurrences  INTEGER NOT NULL DEFAULT 0
);
```

## 実装ステップ

各ステップは独立にテスト可能な粒度で切る。

### Step 1: プロジェクト骨格（uv）
- `uv init --package english-coach` でプロジェクトを初期化（`pyproject.toml` と `.python-version` が生成）
- `uv add fastapi uvicorn anthropic python-dotenv httpx` で依存を追加
- `.env.example`（`ANTHROPIC_API_KEY=` のみ）, `.gitignore`（`data/`, `.env`, `__pycache__/`, `.venv/`）を作成。`uv.lock` はコミット対象
- `english_coach/__init__.py`, `english_coach/config.py` を作成
- `config.py`: `DB_PATH`, `SERVER_HOST=127.0.0.1`, `SERVER_PORT=8765`, `MODEL="claude-haiku-4-5-20251001"`, `CLAUDE_PROJECTS_DIR=~/.claude/projects` を集中管理

### Step 2: DB 層
- `english_coach/db.py`: `init_db()`, `insert_correction(...)`, `get_latest(n)`, `get_history(...)`, `get_last_uuid(session_id)`, `set_last_uuid(session_id, uuid)`
- 全関数は接続を都度オープン／クローズ（hook も server も同じ DB を叩く前提、WAL モードを有効化して書き込み競合回避）

### Step 3: JSONL リーダ & 言語判定
- `english_coach/jsonl_reader.py`:
  - `new_user_messages(session_jsonl_path, since_uuid) -> list[{uuid, text, ts}]`
  - 除外ルール: `isMeta=true`, `<command-name>`/`<command-message>`/`<command-args>`/`<local-command-*>` を含む行, `content` が配列（tool_result 等）の行
- `english_coach/language.py`:
  - Unicode ブロック判定で「ひらがな/カタカナ/CJK 漢字」の文字数 vs 英字の文字数を比較、多い方を採用。両方ゼロなら判定不能として `None` を返し hook 側でスキップ

### Step 4: Corrector（Claude API）
- `english_coach/corrector.py`:
  - `correct(text, language) -> {correction, explanation}`
  - プロンプトはシステム側に固定（JP→英語変換 or EN→自然化）。タイムアウト 8 秒、失敗時は例外を吐かず `None` を返す
  - `anthropic.Anthropic()` は関数外で 1 回だけ初期化（モジュールレベル）

### Step 5: Stop hook 本体
- `english_coach/hook.py` (`uv run python -m english_coach.hook`):
  1. stdin から JSON（Claude Code が渡す hook payload）を読み、`session_id`/`cwd`/`transcript_path` を取得
  2. `last_processed_uuid = db.get_last_uuid(session_id)`
  3. 新規ユーザーメッセージを抽出 → 言語判定 → 補正 → `httpx.post('/api/feedback', ...)`（`requests` ではなく `httpx` で統一）
  4. 最後に `db.set_last_uuid(session_id, 最新uuid)`
  5. **全例外を捕捉して `sys.exit(0)`**（設計書の「非ブロッキング」原則）
- サーバー未起動時にも Claude Code が止まらないよう、POST 失敗はログファイルに記録して終了

### Step 6: FastAPI サーバー
- `server.py`:
  - `GET /` → `static/index.html` を返す（`StaticFiles` マウント）
  - `POST /api/feedback` → Pydantic モデルでバリデーション → `db.insert_correction`
  - `POST /api/summary` → `db.insert_summary`
  - `GET /api/latest?limit=20`
  - `GET /api/history?session_id=&limit=50&offset=0`
  - CORS は localhost のみ許可
  - 起動時に `db.init_db()` を呼ぶ（lifespan event）

### Step 7: ダッシュボード
- `static/index.html`: 単一ファイル、外部依存なし（Tailwind は CDN でも可、ただし v1 はプレーン CSS で十分）
- 画面構成:
  - ヘッダ: 「English Coach」+ 最終更新時刻
  - 最新補正カード（一番上、ハイライト、`ts` 降順で最新1件）
  - セッション履歴リスト: 各行に `言語バッジ / 原文 / → / 補正 / 解説（折りたたみ）`
  - フィルタ: `今日 / このセッション / すべて`（クエリパラメータで切替）
- 2 秒 `setInterval` で `/api/latest` をポーリング。最新の `id` が変わったら差分だけ先頭に挿入（全再描画しない）

### Step 8: Claude Code との結線
- `.claude/settings.json` の `"Stop": []` を以下に差し替え:
  ```json
  "Stop": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "command",
          "command": "cd \"$CLAUDE_PROJECT_DIR\" && uv run python -m english_coach.hook"
        }
      ]
    }
  ]
  ```
- hook は非ブロッキング（例外時 exit 0）なので Claude Code 体験を損なわない

## 参照する既存コード

- `.claude/hooks/protect-files.sh`: hook 入力 payload が stdin から JSON で渡るパターンのお手本（`jq -r '.tool_input.file_path'` と同じ構造を Python 側で再現）
- `.claude/hooks/block-rm.sh`: hook 失敗時の出力規約
- `~/.claude/projects/<project>/<session>.jsonl` のフォーマット（本計画策定時に実サンプルで確認済み）:
  - 各行 JSON、`type` が `user`/`assistant`/`permission-mode`/`file-history-snapshot` 等
  - ユーザー入力メッセージは `type=user`, `isMeta!=true`, `content` が文字列
  - slash command は `content` に `<command-name>` 等のタグを含む（除外対象）

## 検証計画

### 単体確認
1. `uv run python -c "from english_coach.language import detect; print(detect('こんにちは、can you help?'))"` → `ja`（混在時は多数派）
2. `uv run python -c "from english_coach.jsonl_reader import new_user_messages; print(new_user_messages('<固定jsonl>', None))"` → 実際のユーザー発話だけが出る
3. `uv run python -c "from english_coach.corrector import correct; print(correct('サーバーを立ち上げてください','ja'))"` → 英訳が返る

### 統合確認（E2E）
1. `uv sync && cp .env.example .env`（`ANTHROPIC_API_KEY` を記入）
2. `uv run python server.py &`  → `curl http://127.0.0.1:8765/api/latest` が `[]` を返す
3. ブラウザで `http://127.0.0.1:8765/` を開く
4. 別ターミナルで `claude` を起動 → 「日本のサーバーを立ち上げて」と日本語で話し、レスポンスを待ってセッションを停止
5. **3 秒以内** にダッシュボードへ補正カードが表示されることを確認（成功基準その1）
6. 英語でも同じ確認: 「can you start server for me」 → より自然な表現に補正
7. セッションを跨いだ後に再度 `/api/history?session_id=...` を叩き、履歴が残っていることを確認（成功基準その2）

### 失敗モードの確認
- サーバーを落とした状態で Claude Code の Stop を発火 → Claude Code 側は止まらない、hook はエラーログを吐くだけ
- `ANTHROPIC_API_KEY` 未設定 → 同上（hook が静かに exit 0）
- JSONL の最後の行が壊れた JSON → `new_user_messages` が該当行をスキップして続行

## スコープ外（TODOS.md の通り v2 以降）

- launchd による常駐化（`TODOS.md` 筆頭項目）
- SRS（patterns テーブルの集計・復習キュー・通知）
- クラウド同期、モバイル対応
- セッション終了時の自動サマリー生成（スキーマは用意するが v1 は手動 POST 可とだけしておく）

## Open Questions

- セッションサマリー生成を v1 に含めるか？ 設計書 "Scope" には入っているが、「3 秒以内応答」はリアルタイム補正の話なので、サマリーは時間制約なしの別ルートで可。v1 では **エンドポイントと画面だけ用意し、生成トリガは後で決める**方針とする（=実質 v1 後回し）。実装を今やるべきなら Step 5.5 を追加する。
