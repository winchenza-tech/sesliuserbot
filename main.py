import os
import sys
import asyncio
from threading import Thread
from flask import Flask
from pyrogram import Client, filters, idle
from pyrogram.raw.functions.phone import CreateGroupCall, LeaveGroupCall
from pyrogram.raw.functions.messages import GetFullChat

# --- DEDEKTİF MODU BAŞLIYOR ---
print(">>> 1. Sistem Başlatılıyor...")

# Python'un güvenlik limitini artıralım (Hata buysa bypass etsin)
try:
    sys.set_int_max_str_digits(100000)
    print(">>> 2. Python sayı limiti genişletildi.")
except Exception:
    print(">>> 2. Limit genişletme gerekmedi (Python sürümü eski olabilir).")

# --- FLASK AYARLARI ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot Çalışıyor"

def run_flask():
    print(">>> Flask sunucusu başlatılıyor...")
    # PORT değişkenini kontrol ediyoruz
    raw_port = os.environ.get("PORT", "5000")
    print(f">>> PORT değeri okunuyor... Uzunluk: {len(str(raw_port))}")
    try:
        port = int(raw_port)
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"!!! HATA: PORT değişkeninde sorun var! Hata: {e}")

# --- BOT AYARLARI KONTROLÜ ---
print(">>> 3. Değişkenler okunuyor...")

raw_api_id = os.environ.get("API_ID", "0")
raw_target_id = os.environ.get("TARGET_GROUP_ID", "0")
session_string = os.environ.get("SESSION_STRING", "")

print(f">>> API_ID ham uzunluk: {len(raw_api_id)}")
print(f">>> TARGET_GROUP_ID ham uzunluk: {len(raw_target_id)}")
print(f">>> SESSION_STRING ham uzunluk: {len(session_string)}")

# Tek tek çevirmeyi deneyelim
try:
    print(">>> API_ID sayıya çevriliyor...")
    API_ID = int(raw_api_id)
    print(">>> API_ID Başarılı.")
except Exception as e:
    print(f"!!! PATLADI: Sorun API_ID değişkeninde! Hata: {e}")
    exit(1)

try:
    print(">>> TARGET_GROUP_ID sayıya çevriliyor...")
    TARGET_GROUP_ID = int(raw_target_id)
    print(">>> TARGET_GROUP_ID Başarılı.")
except Exception as e:
    print(f"!!! PATLADI: Sorun TARGET_GROUP_ID değişkeninde! Hata: {e}")
    exit(1)

API_HASH = os.environ.get("API_HASH")

# --- BOT BAŞLATILIYOR ---
print(">>> 4. Bot Client oluşturuluyor...")
bot = Client("sesli_bot", session_string=session_string, api_id=API_ID, api_hash=API_HASH)

@bot.on_message(filters.command("sesliac") & filters.group)
async def sesli_yonetimi(client, message):
    if message.chat.id != TARGET_GROUP_ID:
        return

    try:
        peer = await client.resolve_peer(message.chat.id)
        await client.invoke(CreateGroupCall(peer=peer, random_id=client.rnd_id()))
        msg = await message.reply("✅ Sesli sohbet başlatıldı.")
        
        await asyncio.sleep(10)
        
        full_chat = await client.invoke(GetFullChat(peer=peer))
        call_info = full_chat.full_chat.call
        if call_info:
            await client.invoke(LeaveGroupCall(call=call_info, source=0))
            await msg.edit("✅ Bot ayrıldı.")
            
    except Exception as e:
        await message.reply(f"Hata: {e}")
        print(f"Hata detayı: {e}")

async def main():
    Thread(target=run_flask).start()
    
    print(">>> 5. Bot bağlanıyor...")
    await bot.start()
    print(">>> 6. Bot başarıyla bağlandı! Diyaloglar çekiliyor...")
    
    async for dialog in bot.get_dialogs():
        pass 
    print(">>> 7. Diyaloglar alındı. Bot göreve hazır.")
    
    await idle()
    await bot.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
