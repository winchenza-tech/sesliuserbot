import os
import asyncio
from threading import Thread
from flask import Flask
from pyrogram import Client, filters
from pyrogram.raw.functions.phone import CreateGroupCall, LeaveGroupCall
from pyrogram.raw.functions.messages import GetFullChat

# --- RENDER İÇİN WEBSERVER (Kapanmayı önler) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Sesli Sohbet Botu Aktif!"

def run_flask():
    # Render'ın atadığı portu dinle, yoksa 5000 kullan
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- AYARLAR VE DEĞİŞKENLER ---
# HATA DÜZELTME: API_ID ve GROUP_ID mutlaka int() içine alınmalıdır.
try:
    API_ID = int(os.environ.get("API_ID", 0))
    API_HASH = os.environ.get("API_HASH")
    SESSION_STRING = os.environ.get("SESSION_STRING")
    TARGET_GROUP_ID = int(os.environ.get("TARGET_GROUP_ID", 0))
except ValueError:
    print("HATA: API_ID veya TARGET_GROUP_ID sayısal değil! Env Variables kontrol et.")
    exit(1)

# Botu Başlatma
bot = Client(
    "sesli_yonetici_bot",
    session_string=SESSION_STRING,
    api_id=API_ID,
    api_hash=API_HASH
)

# --- ANA FONKSİYON: SESLİ SOHBETİ AÇ VE ÇIK ---
@bot.on_message(filters.command("sesliac") & filters.chat(TARGET_GROUP_ID))
async def sesli_yonetimi(client, message):
    try:
        # Sohbetin teknik ID'sini (Peer) çöz
        peer = await client.resolve_peer(message.chat.id)
        
        # 1. Sesli Sohbeti Başlat
        await client.invoke(
            CreateGroupCall(
                peer=peer,
                random_id=client.rnd_id()
            )
        )
        msg = await message.reply("✅ Sesli sohbet başlatıldı. 10 saniye sonra listeden çıkacağım... Sesli sohbette sorun varsa 20-30 saniye sonra tekrar deneyin.")
        print(f"Sesli sohbet başlatıldı: {message.chat.title}")

        # 2. 10 Saniye Bekle
        await asyncio.sleep(10)

        # 3. Aktif Sohbet Bilgisini Al (Call ID lazım)
        full_chat_data = await client.invoke(GetFullChat(peer=peer))
        group_call = full_chat_data.full_chat.call

        # 4. Sohbetten Ayrıl (Leave)
        if group_call:
            await client.invoke(LeaveGroupCall(call=group_call, source=0))
            await msg.edit("✅ Sesli sohbet başlatıldı. (Bot ayrıldı)")
            print("Bot sesli sohbetten ayrıldı.")
        else:
            print("Aktif çağrı bulunamadı, zaten kapanmış olabilir.")

    except Exception as e:
        # Hata olursa gruba bildir
        await message.reply(f"❌ Hata oluştu: {e}")
        print(f"HATA DETAYI: {e}")

if __name__ == "__main__":
    # Web sunucusunu arka planda başlat
    Thread(target=run_flask).start()
    
    # Botu başlat
    print("Bot başlatılıyor...")
    bot.run()
