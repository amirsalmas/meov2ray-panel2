import os
import sqlite3
import uuid
import random
import string
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI(title="MeoPasarGuard")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

DB_PATH = "panel.db"

# --- توابع کمکی دیتابیس ---
def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            uuid TEXT UNIQUE,
            data_limit_gb INTEGER,
            expire_days INTEGER,
            created_at TEXT
        )
    """)
    con.commit()
    con.close()

init_db()

def generate_uuid():
    return str(uuid.uuid4())

def generate_sub_id():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

def build_vless_link(user_uuid, username):
    # در اینجا آی‌پی سرور واقعی خودت رو بذار (یا از متغیر محیطی لوسیتی بخون)
    server_ip = os.getenv("SERVER_IP", "127.0.0.1")
    return f"vless://{user_uuid}@{server_ip}:443?type=tcp&security=reality&pbk=YOUR_PUBLIC_KEY&fp=chrome&sni=www.microsoft.com&sid=1234567890abcdef&flow=xtls-rprx-vision#{username}"

# --- روت‌های وب پنل ---
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    users = con.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    con.close()
    
    users_list = []
    for u in users:
        user_dict = dict(u)
        user_dict['vless_link'] = build_vless_link(u['uuid'], u['username'])
        users_list.append(user_dict)
        
    # روش صحیح رندر کردن تمپلیت در FastAPI جدید
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"users": users_list}
    )

@app.post("/add_user")
async def add_user(username: str = Form(...), data_limit_gb: int = Form(0), days: int = Form(30)):
    user_uuid = generate_uuid()
    created_at = datetime.now().isoformat()
    
    con = sqlite3.connect(DB_PATH)
    try:
        con.execute("INSERT INTO users (username, uuid, data_limit_gb, expire_days, created_at) VALUES (?, ?, ?, ?, ?)",
                    (username, user_uuid, data_limit_gb, days, created_at))
        con.commit()
    except sqlite3.IntegrityError:
        pass # اگر نام کاربری تکراری بود، ارور نده
    finally:
        con.close()

    return RedirectResponse(url="/", status_code=303)

@app.post("/delete_user/{user_id}")
async def delete_user(user_id: int):
    con = sqlite3.connect(DB_PATH)
    con.execute("DELETE FROM users WHERE id = ?", (user_id,))
    con.commit()
    con.close()
    return RedirectResponse(url="/", status_code=303)

@app.get("/api/status")
async def status():
    return {"status": "online", "panel": "MeoPasarGuard"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
