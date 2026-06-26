# Personal Learning & Workspace

一個以 Flask 建立的個人學習與工作管理系統，用來集中管理學習筆記、待辦事項、專案、問題紀錄與檔案。專案預設使用 SQLite，適合本機開發、個人使用，也可依照 `DEPLOY_PYTHONANYWHERE.md` 部署到 PythonAnywhere。

## 功能特色

- 使用者登入、登出與管理員帳號管理
- Dashboard 統計總覽與近期資料摘要
- 學習筆記管理，支援 Markdown、分類、標籤與收藏
- Todo 管理，支援狀態、優先順序、截止日、提醒時間、Markdown 說明與拖拉排序
- Project 管理，可把 Todo 歸屬到不同專案
- Question Pool，可記錄問題、GPT 回答、理解狀態與完成狀態
- File Manager，支援檔案上傳、下載、刪除與 Markdown/TXT 線上閱讀
- 全站搜尋，支援 Notes、Todos、Projects、Questions、Files
- JSON API，提供主要資料的 CRUD 與 Dashboard 統計
- 響應式介面，支援桌機與手機瀏覽

## 技術架構

- Python 3
- Flask
- Flask-Login
- Flask-SQLAlchemy
- SQLite
- Markdown
- Jinja2 Templates

## 專案結構

```text
.
├── app/
│   ├── routes/              # Web pages 與 API 路由
│   ├── static/              # CSS 等靜態資源
│   ├── templates/           # Jinja2 HTML templates
│   ├── __init__.py          # Flask app factory
│   ├── cli.py               # init-db / upgrade-db / seed 指令
│   ├── config.py            # 設定檔
│   └── models.py            # SQLAlchemy models
├── personal_learning_workspace_app.py
├── run.py                   # 本機啟動入口
├── requirements.txt
├── start_app.bat            # Windows 一鍵啟動
├── DEPLOY_PYTHONANYWHERE.md
└── README.md
```

## 本機啟動

### 1. 建立並啟用虛擬環境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. 安裝依賴

```powershell
python -m pip install -r requirements.txt
```

### 3. 初始化資料庫

```powershell
$env:FLASK_APP = "run.py"
python -m flask upgrade-db
python -m flask seed
```

預設 seed 帳號：

```text
帳號：admin
密碼：admin123
```

### 4. 啟動開發伺服器

```powershell
python run.py
```

預設網址：

```text
http://127.0.0.1:5050
```

Windows 也可以直接執行：

```powershell
.\start_app.bat
```

## Flask CLI 指令

```powershell
$env:FLASK_APP = "run.py"
python -m flask init-db
python -m flask upgrade-db
python -m flask seed-basic
python -m flask seed
```

- `init-db`：建立資料表
- `upgrade-db`：建立資料表並補齊既有資料庫缺少的欄位
- `seed-basic`：只建立預設管理員與基本分類，不建立示範知識內容
- `seed`：建立預設管理員、分類、專案與示範資料

## 環境變數

| 變數 | 說明 | 預設值 |
| --- | --- | --- |
| `SECRET_KEY` | Flask session secret key | `dev-change-me` |
| `DATABASE_URL` | SQLAlchemy database URI | `sqlite:///workspace.db` |
| `UPLOAD_FOLDER` | 上傳檔案儲存目錄 | `uploads` |

正式部署時請務必設定自己的 `SECRET_KEY`，並依需求改用 MySQL 或其他正式資料庫。

## API 概覽

主要 API 皆需登入後使用：

- `GET /api/dashboard/stats`
- `/api/notes`
- `/api/todos`
- `/api/projects`
- `/api/questions`
- `/api/files`
- `GET /api/search?q=keyword`

各資料模組支援常見的 `GET`、`POST`、`PUT`、`DELETE` 操作，檔案模組支援 multipart upload 與 download。

## 部署

PythonAnywhere 部署方式請參考：

```text
DEPLOY_PYTHONANYWHERE.md
```

部署入口模組：

```python
personal_learning_workspace_app.app
```

## 注意事項

- `workspace.db` 是本機 SQLite 資料庫，建議不要提交到 GitHub。
- `uploads/` 會保存使用者上傳檔案，建議不要提交到 GitHub。
- `__pycache__/` 與 `.venv/` 是本機產物，應排除在版本控制之外。
- 預設帳號密碼只適合開發測試，正式環境請立即修改。
