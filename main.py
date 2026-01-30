import os
import asyncio
from threading import Thread
from flask import Flask
from pyrogram import Client, filters, idle
from pyrogram.raw.functions.phone import CreateGroupCall, LeaveGroupCall
from pyrogram.raw.functions.messages import GetFullChat

# --- RENDER HEALTH CHECK ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot Çalışıyor"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

# --- HATA AYIKLAMA (DEBUG) ---
print("--- DEĞİŞKEN KONTROLÜ BAŞLIYOR ---")

raw_api_id = os.environ.get("API_ID", "")
raw_target_id = os.environ.get("TARGET_GROUP_ID", "")

print(f"API_ID Uzunluğu: {len(raw_api_id)} karakter")
print(f"TARGET_GROUP_ID Uzunluğu: {len(raw_target_id)} karakter")

if len(raw_api_id) > 20:
    print("!!! HATA: API_ID çok uzun! Muhtemelen yanlışlıkla Session String'i API_ID kutusuna yapıştırdınız.")
    exit(1)

if len(raw_target_id) > 20:
    print("!!! HATA: TARGET_GROUP_ID çok uzun! Buraya sadece -100 ile başlayan ID yazın.")
    exit(1)

# --- AYARLAR ---
try:
    API_ID = int(raw_api_id)
    TARGET_GROUP_ID = int(raw_target_id)
    API_HASH = os.environ.get("API_HASH")
    SESSION_STRING = os.environ.get("SESSION_STRING")
except ValueError:
    print("HATA: API_ID veya TARGET_GROUP_ID sayı değil (harf içeriyor).")
    exit(1)

print("--- DEĞİŞKENLER DOĞRU GÖRÜNÜYOR, BOT BAŞLATILIYOR ---")

bot = Client("sesli_bot", session_string=SESSION_STRING, api_id=API_ID, api_hash=API_HASH)

@bot.on_message(filters.command("sesliac") & filters.group)
async def sesli_yonetimi(client, message):
    if message.chat.id != TARGET_GROUP_ID:
        return

    try:
        peer = await client.resolve_peer(message.chat.id)
        await client.invoke(CreateGroupCall(peer=peer, random_id=client.rnd_id()))
        msg = await message.reply("✅ Sesli sohbet başlatıldı. 10 sn sonra çıkıyorum.")
        
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
    await bot.start()
    
    # Peer ID Invalid hatasını çözmek için dialogları çek
    print("Grup listesi güncelleniyor...")
    async for dialog in bot.get_dialogs():
        pass 
    print("Bot hazır!")
    
    await idle()
    await bot.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
