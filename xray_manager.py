import json
import uuid
import os
import subprocess
import random
import string

CONFIG_PATH = "/usr/local/etc/xray/config.json"

def generate_uuid():
    return str(uuid.uuid4())

def generate_sub_id():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

def update_xray_config(users):
    """این تابع کانفیگ Xray رو بر اساس کاربران دیتابیس آپدیت میکنه"""
    # اگر فایل وجود نداشت، یک کانفیگ پایه می‌سازد
    base_config = {
        "log": {"loglevel": "warning"},
        "inbounds": [{
            "port": 443,
            "protocol": "vless",
            "settings": {
                "clients": [],
                "decryption": "none"
            },
            "streamSettings": {
                "network": "tcp",
                "security": "reality",
                "realitySettings": {
                    "show": False,
                    "dest": "www.microsoft.com:443",
                    "xver": 0,
                    "serverNames": ["www.microsoft.com"],
                    "privateKey": "YOUR_PRIVATE_KEY_HERE", # در محیط واقعی باید تولید بشه
                    "shortIds": ["1234567890abcdef"]
                }
            }
        }],
        "outbounds": [{"protocol": "freedom"}]
    }

    for user in users:
        base_config["inbounds"][0]["settings"]["clients"].append({
            "id": user['uuid'],
            "flow": "xtls-rprx-vision",
            "email": user['username']
        })

    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(base_config, f, indent=2)
    
    # ری‌استارت کردن سرویس Xray (اگر روی لینوکس نصب باشه)
    try:
        subprocess.run(["systemctl", "restart", "xray"], check=True)
    except:
        pass # اگر Xray نصب نبود، ارور نده

def build_vless_link(user_uuid, username, server_ip):
    """ساخت لینک کانفیگ VLESS برای کاربر"""
    # این مقادیر باید با کانفیگ بالا همخوانی داشته باشن
    return f"vless://{user_uuid}@{server_ip}:443?type=tcp&security=reality&pbk=YOUR_PUBLIC_KEY&fp=chrome&sni=www.microsoft.com&sid=1234567890abcdef&flow=xtls-rprx-vision#{username}"
