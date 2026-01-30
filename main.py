import os
import sys
import asyncio
import traceback
from threading import Thread
from flask import Flask
from pyrogram import Client, filters, idle
from pyrogram.raw.functions.phone import CreateGroupCall, LeaveGroupCall
# DÜZELTME 1: GetFullChat yerine GetFullChannel import ediyoruz
from pyrogram.raw.functions.channels import GetFullChannel

# --- 1. GÜVENLİK KİLİDİNİ KALDIR ---
try:
    sys.set_int_max_str_digits(0)
except Exception:
    pass

# --- FLASK ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot Çalışıyor"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- AYARLAR ---
try:
    API_ID = int(os.environ.get("API_ID", "0").strip())
    API_HASH = os.environ.get("API_HASH", "").strip()
    SESSION_STRING = os.environ.get("SESSION_STRING", "").strip()
    TARGET_GROUP_ID = int(os.environ.get("TARGET_GROUP_ID", "0").strip())
except Exception as e:
    print(f"Ayar Hatası: {e}")
    exit(1)

bot = Client("sesli_bot", session_string=SESSION_STRING, api_id=API_ID, api_hash=API_HASH)

# --- KOMUT İŞLEYİCİ ---
@bot.on_message(filters.command("sesliac") & filters.group)
async def sesli_yonetimi(client, message):
    if message.chat.id != TARGET_GROUP_ID:
        return

    try:
        status_msg = await message.reply("🔄 İşlem başlıyor...")

        # 1. Peer Çözümleme
        peer = await client.resolve_peer(message.chat.id)
        
        # 2. Sesli Sohbet Başlatma
        import random
        await client.invoke(
            CreateGroupCall(
                peer=peer,
                random_id=random.randint(100000, 999999)
            )
        )
        await status_msg.edit("✅ Sesli sohbet açıldı! 10 saniye sonra çıkıyorum.")
        print(f"Sesli sohbet açıldı: {message.chat.title}")
        
        # 3. Bekleme
        await asyncio.sleep(10)
        
        # 4. Çıkış İşlemi (DÜZELTİLDİ: GetFullChannel kullanıldı)
        # Süper gruplarda (ID -100...) kanal fonksiyonu kullanılır.
        full_chat = await client.invoke(GetFullChannel(channel=peer))
        
        call_info = full_chat.full_chat.call
        if call_info:
            await client.invoke(LeaveGroupCall(call=call_info, source=0))
            await status_msg.edit("✅ Sesli sohbet açıldı. (Bot ayrıldı)")
            print("Bot sesli sohbetten başarıyla ayrıldı.")
        else:
            await status_msg.edit("⚠️ Sesli sohbet zaten kapanmış olabilir.")
            
    except Exception:
        error_trace = traceback.format_exc()
        print(f"HATA:\n{error_trace}")
        if len(error_trace) > 4000: error_trace = error_trace[:4000]
        await message.reply(f"err:\n`{error_trace}`")

async def main():
    Thread(target=run_flask).start()
    print("Bot başlatılıyor...")
    await bot.start()
    
    # Hafızayı tazele
    async for dialog in bot.get_dialogs(): pass
    
    print("Bot hazır!")
    await idle()
    await bot.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
