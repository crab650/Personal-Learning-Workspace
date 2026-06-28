# PythonAnywhere 掛載部署說明

此專案可用 PythonAnywhere 的 WSGI 掛載方式部署。

## 掛載入口

本專案已提供掛載模組：

```python
personal_learning_workspace_app.py
```

內容會暴露：

```python
app
```

因此你的主掛載設定可以加入：

```python
MOUNTED_APPS = [
    ("/dark_chess_arena", "dark_chess_arena.app", "app"),
    ("/material", "material.app", "app"),
    ("/energy", "energy.app", "app"),
    ("/smart_note", "smart_note.personal_learning_workspace_app", "app"),
]
```

如果你的 WSGI 只把 `/home/你的帳號/mysite` 加到 `sys.path`，建議使用：

```python
("/smart_note", "smart_note.personal_learning_workspace_app", "app")
```

如果你另外把 `/home/你的帳號/mysite/smart_note` 也加到 `sys.path`，才使用：

```python
("/smart_note", "personal_learning_workspace_app", "app")
```

## 目錄建議

假設專案放在：

```text
/home/你的帳號/personal_learning_workspace
```

PythonAnywhere WSGI 檔案需把此資料夾加入 `sys.path`：

```python
import sys

project_home = "/home/你的帳號/personal_learning_workspace"
if project_home not in sys.path:
    sys.path.insert(0, project_home)
```

## 主 WSGI 範例

```python
from __future__ import annotations

import sys
from importlib import import_module
from typing import Any
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.wrappers import Response


PROJECTS = [
    "/home/你的帳號/dark_chess_arena",
    "/home/你的帳號/material",
    "/home/你的帳號/energy",
    "/home/你的帳號/personal_learning_workspace",
]

for project_home in PROJECTS:
    if project_home not in sys.path:
        sys.path.insert(0, project_home)


MOUNTED_APPS = [
    ("/dark_chess_arena", "dark_chess_arena.app", "app"),
    ("/material", "material.app", "app"),
    ("/energy", "energy.app", "app"),
    ("/workspace", "personal_learning_workspace_app", "app"),
]


def get_mounted_apps() -> dict[str, Any]:
    mounted_apps = {}

    for mount_path, module_name, app_name in MOUNTED_APPS:
        try:
            module = import_module(module_name)
        except ModuleNotFoundError:
            continue
        mounted_apps[mount_path] = getattr(module, app_name)

    return mounted_apps


def not_found_app(environ, start_response):
    return Response("App not found", status=404)(environ, start_response)


application = DispatcherMiddleware(not_found_app, get_mounted_apps())
```

## 初始化資料庫

第一次部署後，在 PythonAnywhere Bash console 執行：

```bash
cd /home/你的帳號/personal_learning_workspace
python -m pip install --user -r requirements.txt
export FLASK_APP=run.py
python -m flask upgrade-db
python -m flask seed
```

既有站台更新程式後也要再次執行：

```bash
export FLASK_APP=run.py
python -m flask upgrade-db
```

這會保留既有資料，並建立專案分享、操作紀錄與圖片附件需要的資料表及欄位。
分享圖片、筆記圖片與問題圖片另外存放在 `uploads/shared_projects/`、`uploads/note_images/`、`uploads/question_images/`，
搬移或備份站台時必須一併保留。

## Static files

PythonAnywhere Web 設定建議：

```text
URL: /workspace/static/
Directory: /home/你的帳號/personal_learning_workspace/app/static
```

若你掛在 `/smart_note`，Static files 建議：

```text
URL: /smart_note/static/
Directory: /home/你的帳號/personal_learning_workspace/app/static
```

若你不是掛在 `/smart_note`，請把 `/smart_note/static/` 改成你的 mount path。

## 404 檢查

如果開啟 `/smart_note` 或 `/smart_note/` 出現 Not Found，依序確認：

1. PythonAnywhere WSGI 檔案有設定：

```python
application = DispatcherMiddleware(not_found_app, get_mounted_apps())
```

只寫 `MOUNTED_APPS` 不會自動掛載，必須用 `DispatcherMiddleware`。

2. 專案資料夾有加入 `sys.path`，例如：

```python
project_home = "/home/你的帳號/personal_learning_workspace"
if project_home not in sys.path:
    sys.path.insert(0, project_home)
```

3. PythonAnywhere Web 頁面按過 `Reload`。

4. Error log 沒有 `ModuleNotFoundError`。你的 `get_mounted_apps()` 目前會 `continue`，如果 import 失敗，該 app 會被略過，結果就是 404。

5. 如果所有檔案都放在 `/home/你的帳號/mysite/smart_note`，而 WSGI 只有加入 `/home/你的帳號/mysite`，掛載模組應該是：

```python
("smart_note.personal_learning_workspace_app")
```

不是：

```python
("personal_learning_workspace_app")
```

6. 同時測試：

```text
/smart_note
/smart_note/
```

## 注意事項

- `start_app.bat` 只給 Windows 本機使用，PythonAnywhere 不會用它。
- `run.py` 只給本機啟動使用，PythonAnywhere 掛載時使用 `personal_learning_workspace_app.app`。
- SQLite 可先用於第一版；多人長期使用建議後續改 MySQL。
