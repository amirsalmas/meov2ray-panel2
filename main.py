import os
import sqlite3
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn
from xray_manager import generate_uuid, generate_sub_id, update_xray_config, build_vless_link

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

DB_PATH = "panel.db"

def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            uuid TEXT UNIQUE,
            sub_id TEXT UNIQUE,
            data_limit INTEGER, -- 0 for unlimited
            expire_date TEXT,
            created_at TEXT
        )
    """)
    con.commit()
    con.close()

init_db()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    users = con.execute("SELECT * FROM users").fetchall()
    con.close()
    
    # اضافه کردن لینک کانفیگ به اطلاعات هر کاربر
    users_list = []
    for u in users:
        user_dict = dict(u)
        # در اینجا IP سرور خودت رو بذار (یا از متغیر محیطی بخون)
        user_dict['vless_link'] = build_vless_link(u['uuid'], u['username'], os.getenv("SERVER_IP", "127.0.0.1"))
        users_list.append(user_dict)
        
    return templates.TemplateResponse("index.html", {"request": request, "users": users_list})

@app.post("/add_user")
async def add_user(username: str = Form(...), data_limit_gb: int = Form(0), days: int = Form(30)):
    user_uuid = generate_uuid()
    sub_id = generate_sub_id()
    created_at = datetime.now().isoformat()
    expire_date = (datetime.now() + timedelta(days=days)).isoformat() if days > 0 else None
    data_limit_bytes = data_limit_gb * 1024 * 1024 * 1024 if data_limit_gb > 0 else 0

    con = sqlite3.connect(DB_PATH)
    try:
        con.execute("INSERT INTO users (username, uuid, sub_id, data_limit, expire_date, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (username, user_uuid, sub_id, data_limit_bytes, expire_date, created_at))
        con.commit()
    except sqlite3.IntegrityError:
        pass # یوزرنیم تکراری
    finally:
        con.close()

    # آپدیت کانفیگ Xray
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    all_users = con.execute("SELECT * FROM users").fetchall()
    con.close()
    update_xray_config(all_users)

    return RedirectResponse(url="/", status_code=303)

@app.post("/delete_user/{user_id}")
async def delete_user(user_id: int):
    con = sqlite3.connect(DB_PATH)
    con.execute("DELETE FROM users WHERE id = ?", (user_id,))
    con.commit()
    
    con.row_factory = sqlite3.Row
    all_users = con.execute("SELECT * FROM users").fetchall()
    con.close()
    update_xray_config(all_users)
    
    return RedirectResponse(url="/", status_code=303)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
