"""
Server FastAPI chay tren Render.
Nhan anh JPEG tu ESP32, detect mat bang OpenCV Haar Cascade.
Neu co mat -> ping Telegram + luu lich su (ngay gio phat hien).
Co trang web /  de xem lich su + anh gan nhat.
"""

import os
import time
import threading
from datetime import datetime, timezone, timedelta

import cv2
import numpy as np
import requests
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse

app = FastAPI()

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

ALERT_COOLDOWN_SECONDS = 15
last_alert_time = 0

VN_TZ = timezone(timedelta(hours=7))

# Luu trang thai trong RAM (don gian, du dung cho 1 camera)
state_lock = threading.Lock()
state = {
    "last_image": None,          # bytes anh JPEG gan nhat nhan duoc
    "last_image_time": None,     # string ngay gio anh gan nhat
    "last_face_time": None,      # string ngay gio LAN GAN NHAT phat hien mat
    "total_faces_detected": 0,   # tong so lan phat hien (theo cooldown)
    "history": [],               # list cac lan phat hien gan day (toi da 50)
}

MAX_HISTORY = 50


def now_vn_string():
    return datetime.now(VN_TZ).strftime("%d/%m/%Y %H:%M:%S")


def send_telegram_alert(jpeg_bytes: bytes, caption: str):
    if not BOT_TOKEN or not CHAT_ID:
        print("Chua cau hinh BOT_TOKEN/CHAT_ID, bo qua gui Telegram.")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    files = {"photo": ("vuon.jpg", jpeg_bytes, "image/jpeg")}
    data = {"chat_id": CHAT_ID, "caption": caption}
    try:
        resp = requests.post(url, data=data, files=files, timeout=10)
        if resp.status_code == 200:
            print("Da gui canh bao Telegram thanh cong.")
        else:
            print(f"Loi gui Telegram: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"Exception khi gui Telegram: {e}")


@app.post("/upload")
async def upload_image(request: Request):
    global last_alert_time

    body = await request.body()
    if not body:
        return Response(content="empty body", status_code=400)

    np_arr = np.frombuffer(body, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if img is None:
        return Response(content="invalid image", status_code=400)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(40, 40),
    )

    face_count = len(faces)
    now = time.time()
    now_str = now_vn_string()

    with state_lock:
        state["last_image"] = body
        state["last_image_time"] = now_str

    alert_sent = False
    if face_count > 0 and (now - last_alert_time) > ALERT_COOLDOWN_SECONDS:
        last_alert_time = now
        caption = f"\U0001F6A8 Phat hien {face_count} nguoi trong vuon sau rieng!\n\U0001F550 {now_str}"
        send_telegram_alert(body, caption)
        alert_sent = True

        with state_lock:
            state["last_face_time"] = now_str
            state["total_faces_detected"] += 1
            state["history"].insert(0, {"time": now_str, "faces": face_count})
            state["history"] = state["history"][:MAX_HISTORY]

    return {"status": "ok", "faces_detected": face_count, "alert_sent": alert_sent}


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    with state_lock:
        last_image_time = state["last_image_time"] or "Chua co anh"
        last_face_time = state["last_face_time"] or "Chua phat hien"
        total = state["total_faces_detected"]
        history = list(state["history"])
        has_image = state["last_image"] is not None

    rows = ""
    if history:
        for h in history:
            rows += f"<tr><td>{h['time']}</td><td>{h['faces']} nguoi</td></tr>"
    else:
        rows = "<tr><td colspan='2' style='text-align:center;color:#888'>Chua co lich su</td></tr>"

    img_tag = (
        "<img src='/latest.jpg' alt='Anh gan nhat'>"
        if has_image
        else "<div style='padding:40px;color:#a8d8a8;text-align:center'>Chua co anh</div>"
    )

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="1">
<title>AI Canh Bao Vuon Sau Rieng</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,Roboto,sans-serif;background:#1a1a2e;color:#fff;padding:16px}}
.container{{max-width:480px;margin:0 auto}}
.header{{text-align:center;padding:16px 0;position:relative}}
h1{{font-size:20px;font-weight:700}}
.reload-btn{{position:absolute;right:0;top:16px;background:#e94560;color:#fff;border:none;
border-radius:50%;width:36px;height:36px;font-size:18px;cursor:pointer}}
.img-box{{background:rgba(255,255,255,0.08);border-radius:16px;padding:12px;margin:14px 0;text-align:center}}
img{{width:100%;border-radius:8px;max-height:300px;object-fit:contain}}
.card{{background:rgba(255,255,255,0.08);border-radius:16px;padding:14px;margin-bottom:12px}}
.card-title{{font-size:12px;color:#a8a8d8;text-transform:uppercase;margin-bottom:6px}}
.card-value{{font-size:18px;font-weight:700}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
td{{padding:8px;border-bottom:1px solid rgba(255,255,255,0.1)}}
.footer{{text-align:center;font-size:11px;color:#6a6a9a;padding:12px 0}}
</style>
</head>
<body><div class="container">
<div class="header">
<button class="reload-btn" onclick="window.location.reload()">&#x21bb;</button>
<h1>AI Canh Bao Vuon Sau Rieng</h1>
</div>
<div class="img-box">{img_tag}</div>
<div class="grid">
<div class="card"><div class="card-title">Anh gan nhat</div><div class="card-value" style="font-size:13px">{last_image_time}</div></div>
<div class="card"><div class="card-title">Phat hien gan nhat</div><div class="card-value" style="font-size:13px">{last_face_time}</div></div>
</div>
<div class="card"><div class="card-title">Tong so lan phat hien</div><div class="card-value">{total}</div></div>
<div class="card">
<div class="card-title">Lich su phat hien</div>
<table>{rows}</table>
</div>
<div class="footer">Tu dong reload moi 1 giay - bam nut tron de reload tay</div>
</div></body></html>"""
    return HTMLResponse(content=html)


@app.get("/latest.jpg")
async def latest_image():
    with state_lock:
        img = state["last_image"]
    if not img:
        return Response(content="no image", status_code=404)
    return Response(content=img, media_type="image/jpeg")
    
