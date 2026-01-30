import os
import sys
import asyncio
import traceback
import random
from threading import Thread
from flask import Flask
from pyrogram import Client, filters, idle
# Gerekli fonksiyonlar
from pyrogram.raw.functions.phone import CreateGroupCall, LeaveGroupCall, DiscardGroupCall
from pyrogram.raw.functions.channels import GetFullChannel

# --- GÜVENLİK KİLİDİNİ KALDIR ---
try:
    sys.set_int_max_str_digits(0)
except Exception:
    pass

# --- FLASK (Web Server) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot Aktif"

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

# ---------------------------------------------------------
# KOMUT 1: /sesliac (Kontrollü Açma)
# ---------------------------------------------------------
@bot.on_message(filters.command("sesliac") & filters.group)
async def sesli_ac(client, message):
    if message.chat.id != TARGET_GROUP_ID: return

    try:
        msg = await message.reply("🔍 Kontrol ediliyor...")
        peer = await client.resolve_peer(message.chat.id)
        
        # ÖNCE KONTROL ET: Sesli sohbet var mı?
        full_chat = await client.invoke(GetFullChannel(channel=peer))
        existing_call = full_chat.full_chat.call

        if existing_call:
            # EĞER AÇIKSA: Uyarı mesajı ver ve dur.
            await msg.edit("⚠️ **Sesli sohbet zaten açık.\nEğer hala sorun yaşıyorsan \n`/seslireset` yazabilirsin. Eğer sorun devam ederse \nZenithar'ı etiketleyin belki sizi görmezden gelmez.")
            return # Fonksiyonu burada bitir
        
        # EĞER KAPALIYSA: Açma işlemine devam et
        await msg.edit("🔄 Sesli sohbet başlatılıyor...")
        await client.invoke(CreateGroupCall(peer=peer, random_id=random.randint(100000, 999999)))
        await msg.edit("✅ Sesli sohbet açıldı! 20 saniye sonra listeden çıkacağım.")
        
        await asyncio.sleep(20)
        
        # Listeden Çık
        # Durum değişmiş olabilir, taze bilgi alalım
        full_chat_new = await client.invoke(GetFullChannel(channel=peer))
        call_info = full_chat_new.full_chat.call
        
        if call_info:
            await client.invoke(LeaveGroupCall(call=call_info, source=0))
            await msg.edit("✅ Sesli sohbet açıldı. Doluşun")
        
    except Exception as e:
        await message.reply(f"❌ Hata: {e}")

# ---------------------------------------------------------
# KOMUT 2: /seslireset (Zorla Kapatıp Açar)
# ---------------------------------------------------------
@bot.on_message(filters.command("seslireset") & filters.group)
async def sesli_reset(client, message):
    if message.chat.id != TARGET_GROUP_ID: return

    try:
        msg = await message.reply("🔄 Sesli sohbet SIFIRLANIYOR...")
        peer = await client.resolve_peer(message.chat.id)

        # ADIM 1: Mevcut sesli sohbet var mı?
        full_chat = await client.invoke(GetFullChannel(channel=peer))
        call_info = full_chat.full_chat.call

        if call_info:
            await msg.edit("🔻 Mevcut sesli sohbet kapatılıyor...")
            # Kapat
            await client.invoke(DiscardGroupCall(call=call_info))
            await asyncio.sleep(3)
        else:
            await msg.edit("ℹ️ Zaten açık bir sohbet yok, yenisi açılıyor...")

        # ADIM 2: Yeni Aç
        await client.invoke(CreateGroupCall(peer=peer, random_id=random.randint(100000, 999999)))
        await msg.edit(" Yeni sesli sohbet açıldı! 20 saniye sonra çıkacağım. Boş yapmaya devam edebilirsiniz.")

        # ADIM 3: 20 Saniye Bekle
        await asyncio.sleep(20)

        # ADIM 4: Ayrıl
        full_chat_new = await client.invoke(GetFullChannel(channel=peer))
        new_call_info = full_chat_new.full_chat.call

        if new_call_info:
            await client.invoke(LeaveGroupCall(call=new_call_info, source=0))
            await msg.edit("✅ İşlem tamamlandı. (Bot ayrıldı)")
        
    except Exception:
        error_trace = traceback.format_exc()
        if len(error_trace) > 4000: error_trace = error_trace[:4000]
        await message.reply(f"❌ **HATA:**\n`{error_trace}`")

# ---------------------------------------------------------
# BAŞLATMA
# ---------------------------------------------------------
async def main():
    Thread(target=run_flask).start()
    print("Bot başlatılıyor...")
    await bot.start()
    
    # Dialogları güncelle (ID hatalarını önler)
    async for dialog in bot.get_dialogs(): pass
    
    print("Bot hazır!")
    await idle()
    await bot.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
