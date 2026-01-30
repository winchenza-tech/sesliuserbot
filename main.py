import os
import asyncio
from threading import Thread
from flask import Flask
from pyrogram import Client, filters, idle
from pyrogram.raw.functions.phone import CreateGroupCall, LeaveGroupCall
from pyrogram.raw.functions.messages import GetFullChat

# --- RENDER WEB SERVICE ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Çalışıyor!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- AYARLAR ---
try:
    API_ID = int(os.environ.get("API_ID", 0))
    API_HASH = os.environ.get("API_HASH")
    SESSION_STRING = os.environ.get("SESSION_STRING")
    TARGET_GROUP_ID = int(os.environ.get("TARGET_GROUP_ID", 0))
except Exception as e:
    print(f"Ayar hatası: {e}")

bot = Client(
    "sesli_bot",
    session_string=SESSION_STRING,
    api_id=API_ID,
    api_hash=API_HASH
)

# --- SESLİ SOHBET FONKSİYONU ---
# Not: Filtreye ID koymadık, ID kontrolünü içeride yapacağız.
# Bu sayede "Peer Invalid" hatasını filtre aşamasında engelleriz.
@bot.on_message(filters.command("sesliac") & filters.group)
async def sesli_yonetimi(client, message):
    
    # Güvenlik Kontrolü: Komut doğru gruptan mı geldi?
    if message.chat.id != TARGET_GROUP_ID:
        return # Yanlış grupsa hiçbir şey yapma

    try:
        # Peer çözümü
        peer = await client.resolve_peer(message.chat.id)
        
        # 1. Başlat
        await client.invoke(
            CreateGroupCall(
                peer=peer,
                random_id=client.rnd_id()
            )
        )
        msg = await message.reply("✅ Sesli sohbet başlatıldı. 10 saniye sonra sesliden çıkacağım..")
        print(f"Sesli açıldı: {message.chat.title}")

        # 2. Bekle
        await asyncio.sleep(10)

        # 3. Ayrıl
        full_chat = await client.invoke(GetFullChat(peer=peer))
        call_info = full_chat.full_chat.call
        
        if call_info:
            await client.invoke(LeaveGroupCall(call=call_info, source=0))
            await msg.edit("✅ Sesli sohbet başlatıldı. (Bot ayrıldı)")
        
    except Exception as e:
        await message.reply(f"❌ Hata: {e}")
        print(f"HATA: {e}")

async def main():
    # Flask'ı başlat
    Thread(target=run_flask).start()
    
    print("Bot başlatılıyor...")
    await bot.start()
    
    # --- KRİTİK NOKTA: GRUPLARI TANI ---
    # Botun üye olduğu tüm grupları bir kere çeker, böylece ID hatası almazsın.
    print("Sohbet listesi güncelleniyor...")
    try:
        async for dialog in bot.get_dialogs():
            # Sadece hafızaya alması yeterli, işlem yapmaya gerek yok
            pass
        print("✅ Sohbet listesi güncellendi! Bot hazır.")
    except Exception as e:
        print(f"Sohbet listesi alınamadı: {e}")

    # Botu açık tut
    await idle()
    await bot.stop()

if __name__ == "__main__":
    # Async döngüyü başlat
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
