# Personal Learning & Workspace

## 系統規格書 v1.0

---

# 一、系統名稱

Personal Learning & Workspace

中文名稱：

**個人學習與工作管理平台**

---

# 二、系統目標

建立一套個人使用的知識管理平台，用於管理：

* 學習筆記
* Markdown 文件
* 待辦事項
* 工作專案
* AI 產出的內容
* 檔案管理
* API 同步

所有資料皆可透過 REST API 同步至 PythonAnywhere Server。

系統定位：

> Notion + Obsidian + Todo + GitHub Wiki 的簡化版。

---

# 三、技術架構

Backend

* Python
* Flask
* SQLAlchemy
* SQLite（開發）
* MySQL（正式）

Frontend

* Bootstrap 5
* Jinja2 Template
* JavaScript
* Chart.js

Markdown

* Python-Markdown
* Highlight.js（程式碼語法高亮）

API

* RESTful API
* JWT Authentication

部署

* PythonAnywhere

---

# 四、系統模組

## 1 Dashboard

首頁顯示

* 今日待辦
* 最近筆記
* 最近修改文件
* 最近完成工作
* 今日學習時數
* 本月統計

---

## 2 Learning Note（學習筆記）

功能

* 新增筆記
* 編輯筆記
* Markdown 編輯
* Markdown 預覽
* 搜尋
* Tag
* 分類
* 收藏
* 刪除

分類

* ERP
* SQL
* Python
* AI
* English
* Vietnam
* MES
* WMS
* Others

每篇筆記包含

* Title
* Category
* Tag
* Markdown Content
* CreatedAt
* UpdatedAt

---

## 3 Markdown 文件管理

支援

* 上傳 md
* 線上閱讀
* 線上編輯
* 即時 Preview
* 下載 md

未來可增加

* PDF Export
* HTML Export

---

## 4 Todo

功能

新增

修改

完成

取消

刪除

拖拉排序

優先順序

* High
* Medium
* Low

狀態

* Todo
* Doing
* Done
* Cancel

可設定

截止日期

提醒日期

分類

---

## 5 Question Pool（問題池）

紀錄學習時遇到的問題

例如

ERP

MRP 為什麼需要 Forecast？

SQL

Window Function 為什麼比 Group By 好？

AI

RAG 與 Fine-tune 差異？

每個問題可記錄

問題

GPT 回答

是否理解

是否完成

---

## 6 File Manager

管理

Markdown

PDF

Excel

Word

圖片

ZIP

每個檔案包含

名稱

大小

分類

建立時間

更新時間

下載次數

---

## 7 Project

管理工作專案

例如

門禁 API

MES

ERP

能源系統

每個專案可管理

需求

會議記錄

文件

Todo

API 文件

---

## 8 Search

全站搜尋

搜尋

標題

Markdown

Tag

問題

Todo

Project

---

## 9 統計分析

Dashboard

顯示

本月新增筆記

完成 Todo

完成專案

學習分類比例

每月學習時間

折線圖

圓餅圖

Bar Chart

---

# 五、資料庫

主要 Table

Users

Categories

Tags

Notes

Todo

Questions

Projects

Files

ApiLogs

Settings

NoteTags

ProjectFiles

TodoHistory

---

# 六、REST API

Notes

GET /api/notes

POST /api/notes

PUT /api/notes/{id}

DELETE /api/notes/{id}

Todo

GET /api/todos

POST /api/todos

PUT /api/todos/{id}

DELETE /api/todos/{id}

Files

Upload

Download

Delete

Projects

CRUD

Questions

CRUD

Dashboard

Statistics

Search

Global Search

---

# 七、首頁畫面

左側 Menu

Dashboard

Learning Notes

Todo

Questions

Projects

Files

Statistics

Settings

首頁

今日待辦

最近筆記

最近修改

今日學習

最近專案

快速新增

---

# 八、Markdown 功能

支援

# 標題

表格

Code Block

Mermaid

Task List

Quote

Image

Link

數學公式（後續）

即時 Preview

Syntax Highlight

Dark Mode

---

# 九、同步功能

提供 API

本機 Python

↓

REST API

↓

PythonAnywhere

↓

Database

支援

新增

修改

刪除

同步時間

同步紀錄

---

# 十、第二階段功能（未來）

AI Chat

NotebookLM 匯出

GitHub Sync

Google Drive Sync

Calendar

每日學習提醒

Email Reminder

全文搜尋

OCR

向量搜尋（RAG）

AI 助手

語音筆記

Mobile Web

PWA

---

# 十一、開發原則

* 模組化架構
* Repository Pattern
* Service Layer
* RESTful API
* MVC
* Bootstrap Responsive UI
* 所有資料皆可透過 API 操作
* 所有 Markdown 可直接閱讀與編輯
* 後續容易擴充 AI Agent 與知識庫功能

---

# 十二、第一版開發目標（MVP）

優先完成以下功能：

✅ 使用者登入

✅ Dashboard

✅ Learning Notes（Markdown）

✅ Todo

✅ Markdown Viewer

✅ File Upload

✅ Search

✅ REST API

完成以上功能即可作為日常學習與工作管理平台使用。
