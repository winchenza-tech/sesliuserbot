import os
import asyncio
from threading import Thread
from flask import Flask
from pyrogram import Client, filters
from pyrogram.raw.functions.phone import CreateGroupCall, LeaveGroupCall
from pyrogram.raw.functions.messages import GetFullChat

# --- RENDER İÇİN SAĞLIK KONTROLÜ (Web Service için şart) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Sesli Sohbet Botu Aktif!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- AYARLAR ---
# Render panelindeki Environment Variables kısmından çekilir
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
# Grup ID'sini aşağıya direkt yazabilirsin (Örn: -10012345678) 
# veya Render'dan TARGET_GROUP_ID adıyla ekleyebilirsin.
TARGET_GROUP_ID = int(os.getenv("TARGET_GROUP_ID"))

bot = Client(
    "sesli_bot",
    session_string=SESSION_STRING,
    api_id=API_ID,
    api_hash=API_HASH
)

# SESLİ SOHBETİ BAŞLAT VE 10 SANİYE SONRA AYRIL
@bot.on_message(filters.command("sesliac") & filters.chat(TARGET_GROUP_ID))
async def start_voice_logic(client, message):
    try:
        peer = await client.resolve_peer(message.chat.id)
        
        # 1. Sesli Sohbeti Başlat
        await client.invoke(
            CreateGroupCall(
                peer=peer,
                random_id=client.rnd_id()
            )
        )
        await message.reply("✅ Sesli sohbet açıldı. 10 saniye içinde ayrılıyorum...")

        # 2. 10 Saniye Bekle
        await asyncio.sleep(10)

        # 3. Aktif Sohbetin Bilgisini Al ve Ayrıl
        full_chat = await client.invoke(GetFullChat(peer=peer))
        call_info = full_chat.full_chat.call

        if call_info:
            await client.invoke(LeaveGroupCall(call=call_info, source=0))
            print(f"Sohbetten ayrılındı: {message.chat.title}")
            
    except Exception as e:
        await message.reply(f"❌ Bir hata oluştu: {e}")

if __name__ == "__main__":
    # Flask sunucusunu ayrı bir koldan başlat
    Thread(target=run_flask).start()
    # Botu çalıştır
    print("Userbot başlatıldı...")
    bot.run()
