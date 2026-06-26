# Personal Learning & Workspace 開發狀態

更新日期：2026-06-26

## 已完成

### 專案基礎

- [x] Flask 專案骨架
- [x] `start_app.bat` 一鍵啟動
- [x] 預設使用 Port `5050`
- [x] SQLite 開發資料庫
- [x] Seed 指令建立預設管理員與示範資料
- [x] 預設帳號：`admin / admin123`

### 使用者與權限

- [x] 登入
- [x] 登出
- [x] 多人使用資料邊界
- [x] 核心資料表支援 `user_id`

### Dashboard

- [x] Dashboard 首頁版面
- [x] 左側選單
- [x] 上方搜尋框
- [x] 統計卡片
- [x] 最近筆記區塊
- [x] 待解決問題區塊
- [x] 今日待辦區塊
- [x] 最近上傳檔案區塊
- [x] Dashboard 統計 API：`/api/dashboard/stats`

### Todo 初版

- [x] Todo 資料模型
- [x] 支援優先順序 `High / Medium / Low`
- [x] 支援狀態 `Todo / Doing / Done / Cancel`
- [x] 支援 `sort_order`
- [x] Dashboard 拖拉排序
- [x] Todo 排序 API：`/api/todos/reorder`

### Todo 完整管理

- [x] Todo 列表頁
- [x] 新增 Todo
- [x] 編輯 Todo
- [x] 刪除 Todo
- [x] 狀態切換
- [x] 截止日期
- [x] 提醒日期
- [x] Todo 說明支援 Markdown
- [x] Todo 說明 Markdown 即時預覽
- [x] Todo CRUD API

### Todo 視角升級

- [x] 依狀態檢視 Todo
- [x] 依分類檢視 Todo
- [x] 依專案檢視 Todo
- [x] Todo 支援專案欄位
- [x] Todo 表單可選擇既有專案
- [x] Todo 表單可直接建立新專案
- [x] Todo API 支援 `project_id`
- [x] Todo API 支援 `project_name`

### Project Lite

- [x] Project 資料模型
- [x] `projects` 資料表
- [x] 預設專案 seed
- [x] 既有資料庫升級指令：`flask upgrade-db`
- [x] `start_app.bat` 啟動前自動升級資料庫

### Project 完整專案模組

- [x] 專案列表
- [x] 新增專案
- [x] 編輯專案
- [x] 刪除專案
- [x] 專案狀態管理
- [x] 專案詳情頁
- [x] 查看專案底下所有 Todo
- [x] Project CRUD API
- [x] 全站搜尋支援 Project

### 啟動器

- [x] `start_app.bat` 檢查 Python 依賴
- [x] `start_app.bat` 自動安裝缺少依賴
- [x] `start_app.bat` 自動開啟瀏覽器
- [x] `start_app.bat` 啟動 Flask Server

### PythonAnywhere 部署準備

- [x] 提供掛載入口：`personal_learning_workspace_app.py`
- [x] 提供 PythonAnywhere 掛載部署文件

### Search 初版

- [x] SQL LIKE 搜尋 API：`/api/search?q=keyword`
- [x] 搜尋 Notes、Todo、Question、Files

### Learning Notes

- [x] 筆記列表
- [x] 新增筆記
- [x] 編輯筆記
- [x] 刪除筆記
- [x] Markdown 預覽
- [x] 分類選擇
- [x] Tag 輸入
- [x] 收藏筆記
- [x] Notes CRUD API

### Question Pool

- [x] 問題列表
- [x] 新增問題
- [x] 編輯問題
- [x] 刪除問題
- [x] 記錄 GPT 回答
- [x] GPT 回答支援 Markdown
- [x] GPT 回答 Markdown 即時預覽
- [x] 標記是否理解
- [x] 標記是否完成
- [x] Question CRUD API

### File Manager

- [x] 檔案列表
- [x] 檔案上傳
- [x] 檔案下載
- [x] 檔案刪除
- [x] Markdown 檔線上閱讀
- [x] 檔案分類
- [x] Files API

### Search 頁面

- [x] 搜尋畫面
- [x] 分組顯示結果
- [x] 點擊結果跳轉
- [x] Search API 回傳跳轉 URL
- [x] 搜尋 Project

### 使用者管理

- [x] 管理員建立使用者頁面
- [x] 修改密碼
- [x] 使用者停用
- [x] 使用者啟用
- [x] 權限管理
- [x] 停用帳號禁止登入
- [x] 既有資料庫升級欄位：`users.is_active_flag`

### Mobile UI

- [x] 手機頂部工具列
- [x] 手機底部導覽列
- [x] 手機版 Dashboard 單欄/雙欄調整
- [x] 手機版表格轉直向卡片排列
- [x] 手機版表單與按鈕排版優化
- [x] 手機版 Markdown 編輯/預覽上下排列
- [x] 手機版內容底部安全距離，避免被底部導覽遮住

## 開發中

### Statistics

- [ ] 真實學習時數資料表
- [ ] Chart.js 圖表接真資料
- [ ] 本月學習進度計算
- [ ] 分類學習比例

## 未完成

### 部署

- [x] PythonAnywhere 掛載方式部署設定
- [ ] MySQL 正式環境設定
- [ ] 環境變數設定
- [ ] 上傳目錄設定

## 第二階段功能

- [ ] AI Chat
- [ ] NotebookLM 匯出
- [ ] GitHub Sync
- [ ] Google Drive Sync
- [ ] Calendar
- [ ] Email Reminder
- [ ] OCR
- [ ] 向量搜尋 / RAG
- [ ] PWA
