"""
Server FastAPI chay tren Render.
Nhan anh JPEG tu ESP32 (HTTP POST raw bytes), detect mat nguoi
bang OpenCV Haar Cascade, neu co mat -> gui canh bao + anh qua Telegram.
"""

import os
import time
import cv2
import numpy as np
import requests
from fastapi import FastAPI, Request, Response

app = FastAPI()

# ---- Cau hinh Telegram (doc tu Environment Variables tren Render, KHONG hardcode) ----
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Haar Cascade co san trong opencv-python, khong can download file ngoai
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# Chong spam Telegram: chi gui canh bao toi thieu cach nhau N giay
ALERT_COOLDOWN_SECONDS = 15
last_alert_time = 0


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

    # Decode JPEG bytes -> anh OpenCV
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

    if face_count > 0 and (now - last_alert_time) > ALERT_COOLDOWN_SECONDS:
        last_alert_time = now
        caption = f"\U0001F4F7 Phat hien {face_count} nguoi trong vuon sau rieng!"
        send_telegram_alert(body, caption)
        return {"status": "ok", "faces_detected": face_count, "alert_sent": True}

    return {"status": "ok", "faces_detected": face_count, "alert_sent": False}


@app.get("/")
async def health_check():
    return {"status": "alive"}
