import os
import sys
import asyncio
import traceback
from threading import Thread
from flask import Flask
from pyrogram import Client, filters, idle
from pyrogram.raw.functions.phone import CreateGroupCall, LeaveGroupCall
from pyrogram.raw.functions.messages import GetFullChat

# --- 1. GÜVENLİK KİLİDİNİ TAMAMEN KALDIR (Sıfır = Sınırsız) ---
try:
    sys.set_int_max_str_digits(0)
    print(">>> Python sayı dönüşüm limiti tamamen kaldırıldı (Sınırsız).")
except Exception:
    pass

# --- FLASK ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot Çalışıyor"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

# --- AYARLAR ---
try:
    # Sayıları alırken boşlukları temizle (.strip)
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
    # Yanlış grup kontrolü
    if message.chat.id != TARGET_GROUP_ID:
        return

    try:
        status_msg = await message.reply("🔄 İşlem başlıyor...")

        # 1. Peer Çözümleme
        peer = await client.resolve_peer(message.chat.id)
        
        # 2. Sesli Sohbet Başlatma (Hata genelde burada)
        # random_id'yi manuel küçük bir sayı vererek deneyelim
        import random
        random_id = random.randint(1000000, 9999999) 

        await client.invoke(
            CreateGroupCall(
                peer=peer,
                random_id=random_id
            )
        )
        await status_msg.edit("✅ Sesli sohbet açıldı! 10 saniye sonra çıkıyorum.")
        
        # 3. Bekleme ve Çıkış
        await asyncio.sleep(10)
        
        full_chat = await client.invoke(GetFullChat(peer=peer))
        call_info = full_chat.full_chat.call
        if call_info:
            await client.invoke(LeaveGroupCall(call=call_info, source=0))
            await status_msg.edit("✅ Sesli sohbet açıldı. (Bot ayrıldı)")
            
    except Exception:
        # Hatanın tamamını yakala ve gruba at
        error_trace = traceback.format_exc()
        print(f"HATA DETAYI:\n{error_trace}") # Loglara da bas
        
        # Telegram mesaj sınırı 4096 karakterdir, sığmazsa kes
        if len(error_trace) > 4000:
            error_trace = error_trace[:4000]
            
        await message.reply(f"\n`{error_trace}`")

async def main():
    Thread(target=run_flask).start()
    print("Bot başlatılıyor...")
    await bot.start()
    
    # Diyalogları yenile
    async for dialog in bot.get_dialogs():
        pass
    print("Bot hazır ve bekliyor.")
    
    await idle()
    await bot.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
