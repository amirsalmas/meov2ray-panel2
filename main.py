import os
import sqlite3
import uuid
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn

# --- ساخت خودکار پوشه‌ها در صورت نبودن (جلوگیری از کرش) ---
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

app = FastAPI(title="MeoPasarGuard")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

DB_PATH = "panel.db"

# --- ساخت خودکار فایل index.html اگر وجود نداشت ---
HTML_FALLBACK = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8"><title>MEO PASARGUARD</title>
    <style>
        body { background: #0f0f13; color: #d4af37; font-family: Tahoma; text-align: center; padding: 50px; }
        .card { background: #1a1a2e; border: 1px solid #d4af37; border-radius: 10px; padding: 20px; max-width: 600px; margin: auto; }
        input, button { padding: 10px; margin: 5px; border-radius: 5px; border: 1px solid #d4af37; background: #0f0f13; color: white; }
        button { background: #d4af37; color: #1a1a2e; font-weight: bold; cursor: pointer; }
        table { width: 100%; margin-top: 20px; border-collapse: collapse; }
        th, td { border-bottom: 1px solid #333; padding: 10px; text-align: right; }
    </style>
</head>
<body>
    <div class="card">
        <h1>👑 MEO PASARGUARD 👑</h1>
        <form action="/add_user" method="post">
            <input type="text" name="username" placeholder="نام کاربری" required>
            <input type="number" name="data_limit_gb" placeholder="حجم (گیگ) 0=نامحدود" value="0">
            <input type="number" name="days" placeholder="روز 0=نامحدود" value="30">
            <button type="submit">ساخت کاربر</button>
        </form>
        <table>
            <tr><th>یوزر</th><th>حجم</th><th>لینک کانفیگ</th><th>حذف</th></tr>
            {% for u in users %}
            <tr>
                <td>{{ u.username }}</td>
                <td>{{ u.data_limit_gb if u.data_limit_gb > 0 else 'نامحدود' }}</td>
                <td style="font-size:10px; word-break: break-all;">{{ u.vless_link }}</td>
                <td><form action="/delete_user/{{ u.id }}" method="post"><button style="background:red; color:white;">X</button></form></td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""

if not os.path.exists("templates/index.html"):
    with open("templates/index.html", "w", encoding="utf-8") as f:
        f.write(HTML_FALLBACK)

# --- دیتابیس ---
def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, uuid TEXT UNIQUE, data_limit_gb INTEGER, expire_days INTEGER, created_at TEXT)")
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
async def add_user(username: str = Form(...), data_limit_gb: int = Form(0), days: int = Form(30)):
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
