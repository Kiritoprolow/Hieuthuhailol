const express = require('express');
const TelegramBot = require('node-telegram-bot-api');
const { GoogleGenAI } = require('@google/genai');
const app = express();

const BOT_TOKEN = '8838984294:AAGsmgTcS3NyjFBNBrt7lI1ZO-facV0bqR0';
const CHAT_ID = '6428642807';
const GEMINI_API_KEY = process.env.GEMINI_API_KEY || 'YOUR_KEY_HERE';

const bot = new TelegramBot(BOT_TOKEN);
const ai = new GoogleGenAI({ apiKey: GEMINI_API_KEY });

let lastImage = null;
let lastTime = null;
let imageCount = 0;
let personDetections = 0;

app.post('/upload', express.raw({ type: 'image/jpeg', limit: '50kb' }), async (req, res) => {
  if (!req.body || req.body.length === 0) return res.status(400).send('No image');

  lastImage = req.body;
  lastTime = new Date().toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' });
  imageCount++;
  console.log(`Nhan anh #${imageCount}: ${lastImage.length} bytes luc ${lastTime}`);
  res.send('OK');

  try {
    const imageB64 = lastImage.toString('base64');
    const interaction = await ai.interactions.create({
      model: 'gemini-3.5-flash',
      input: [
        { type: 'text', text: 'Co nguoi trong anh nay khong? Chi tra loi CO hoac KHONG, khong giai thich them.' },
        { type: 'image', data: imageB64, mime_type: 'image/jpeg' }
      ]
    });

    const answer = interaction.output_text.trim().toUpperCase();
    console.log('Gemini tra loi:', answer);

    if (answer.includes('CO')) {
      personDetections++;
      await bot.sendPhoto(CHAT_ID, lastImage, {
        caption: `🚨 PHAT HIEN NGUOI!\n📷 Vuon Sau Rieng\n🕐 ${lastTime}\n📡 Anh #${imageCount}`
      });
      console.log('Telegram OK - co nguoi!');
    } else {
      console.log('Khong co nguoi, bo qua Telegram.');
    }
  } catch (e) {
    console.log('LOI Gemini/Telegram:', e.message);
  }
});

app.get('/', (req, res) => {
  const online = lastTime && (Date.now() - new Date(lastTime).getTime() < 120000);
  res.send(`<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="refresh" content="5">
  <title>Vuon Sau Rieng</title>
  <style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{background:#1a3c1a;color:#fff;font-family:-apple-system,sans-serif;padding:16px}
    .container{max-width:480px;margin:0 auto}
    h1{text-align:center;font-size:20px;padding:16px 0}
    .badge{display:block;text-align:center;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;margin:0 auto 16px;width:fit-content}
    .ok{background:#2ecc71;color:#000}
    .warn{background:#e74c3c}
    .img-box{background:rgba(255,255,255,0.08);border-radius:16px;padding:12px;margin-bottom:12px;text-align:center}
    img{width:100%;border-radius:8px;max-height:320px;object-fit:contain}
    .ts{font-size:12px;color:#a8d8a8;margin-top:8px}
    .grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px}
    .card{background:rgba(255,255,255,0.08);border-radius:16px;padding:14px}
    .card-title{font-size:11px;color:#a8d8a8;text-transform:uppercase;margin-bottom:4px}
    .card-value{font-size:16px;font-weight:700}
    .footer{text-align:center;font-size:11px;color:#6a9a6a;padding:12px 0}
  </style>
</head>
<body>
<div class="container">
  <h1>🌿 Vuon Sau Rieng</h1>
  <span class="badge ${online ? 'ok' : 'warn'}">${online ? 'Dang hoat dong' : 'Chua co tin hieu'}</span>
  <div class="img-box">
    ${lastImage
      ? `<img src="/image.jpg" alt="Anh vuon"><div class="ts">📷 ${lastTime}</div>`
      : `<div style="padding:40px;color:#a8d8a8">Chua nhan duoc anh</div>`}
  </div>
  <div class="grid">
    <div class="card">
      <div class="card-title">Tong so anh</div>
      <div class="card-value">${imageCount}</div>
    </div>
    <div class="card">
      <div class="card-title">Phat hien nguoi</div>
      <div class="card-value">${personDetections}</div>
    </div>
  </div>
  <div class="footer">Tu dong cap nhat 5 giay mot lan</div>
</div>
</body>
</html>`);
});

app.get('/image.jpg', (req, res) => {
  if (!lastImage) return res.status(404).send('Chua co anh');
  res.set('Content-Type', 'image/jpeg');
  res.set('Cache-Control', 'no-cache');
  res.send(lastImage);
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server chay port ${PORT}`));
