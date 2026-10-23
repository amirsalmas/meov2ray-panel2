import os
import sqlite3
import uuid
import json
import subprocess
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn

# --- ساخت پوشه‌ها در صورت نبودن (جلوگیری از کرش) ---
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

app = FastAPI(title="MeoPasarGuard")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

DB_PATH = "panel.db"

# --- ساخت خودکار فایل HTML اگر وجود نداشت ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>MEO PASARGUARD</title>
    <style>
        body { background-color: #0f0f13; color: #d4af37; font-family: Tahoma; text-align: center; padding-top: 40px; background-image: url('/static/bg.jpg'); background-size: cover; background-blend-mode: overlay; margin: 0; min-height: 100vh; }
        .box { background: rgba(26, 26, 46, 0.95); border: 1px solid #d4af37; padding: 30px; border-radius: 15px; width: 90%; max-width: 800px; margin: 0 auto; box-shadow: 0 0 20px rgba(212, 175, 55, 0.2); }
        input, button { padding: 10px; margin: 5px; border-radius: 5px; border: 1px solid #d4af37; background: #0f0f13; color: white; }
        button { background: #d4af37; color: #1a1a2e; font-weight: bold; cursor: pointer; transition: 0.3s; }
        button:hover { background: #b8962e; }
        table { width: 100%; margin-top: 20px; border-collapse: collapse; background: #151525; border-radius: 8px; overflow: hidden; }
        th, td { border-bottom: 1px solid #333; padding: 12px; text-align: right; font-size: 14px; }
        th { background: #1a1a2e; color: #d4af37; }
        .config { font-size: 11px; word-break: break-all; color: #aaa; direction: ltr; text-align: left; }
        .btn-del { background: #c0392b; color: white; padding: 5px 10px; border: none; border-radius: 5px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="box">
        <h1>👑 MEO PASARGUARD 👑</h1>
        <p style="color:#aaa;">پنل مدیریت و ساخت کانفیگ هخامنشی</p>
        
        <form action="/add_user" method="post" style="margin-bottom: 20px;">
            <input type="text" name="username" placeholder="نام کاربری" required>
            <input type="number" name="data_limit_gb" placeholder="حجم (گیگ - 0 نامحدود)" value="90">
            <input type="number" name="days" placeholder="مدت (روز - 0 نامحدود)" value="30">
            <button type="submit">ساخت کاربر</button>
        </form>

        <table>
            <tr><th>کاربر</th><th>حجم</th><th>انقضا</th><th>کانفیگ (VLESS)</th><th>حذف</th></tr>
            {% for u in users %}
            <tr>
                <td><b>{{ u.username }}</b></td>
                <td>{{ u.data_limit_gb if u.data_limit_gb > 0 else 'نامحدود' }}</td>
                <td>{{ u.expire_days if u.expire_days > 0 else 'نامحدود' }}</td>
                <td class="config">{{ u.vless_link }}</td>
                <td>
                    <form action="/delete_user/{{ u.id }}" method="post">
                        <button type="submit" class="btn-del">X</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>
    <audio id="bg-music" autoplay loop>
        <source src="/static/music-panel.mp3" type="audio/mpeg">
    </audio>
</body>
</html>
"""
with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(HTML_TEMPLATE)

# --- دیتابیس ---
def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        uuid TEXT UNIQUE,
        data_limit_gb INTEGER,
        expire_days INTEGER,
        created_at TEXT
    )""")
    con.commit()
    con.close()
init_db()

def build_vless_link(user_uuid, username):
    server_ip = os.getenv("SERVER_IP", "127.0.0.1")
    return f"vless://{user_uuid}@{server_ip}:443?type=tcp&security=reality&pbk=KEY&fp=chrome&sni=www.microsoft.com&sid=1234&flow=xtls-rprx-vision#{username}"

# --- روت‌ها ---
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    users = con.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    con.close()
    
    users_list = []
    for u in users:
        d = dict(u)
        d['vless_link'] = build_vless_link(u['uuid'], u['username'])
        users_list.append(d)
        
    return templates.TemplateResponse(request=request, name="index.html", context={"users": users_list})

@app.post("/add_user")
async def add_user(username: str = Form(...), data_limit_gb: int = Form(0), days: int = Form(0)):
    con = sqlite3.connect(DB_PATH)
    try:
        con.execute("INSERT INTO users (username, uuid, data_limit_gb, expire_days, created_at) VALUES (?, ?, ?, ?, ?)",
                    (username, str(uuid.uuid4()), data_limit_gb, days, datetime.now().isoformat()))
        con.commit()
    except sqlite3.IntegrityError:
        pass
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

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
