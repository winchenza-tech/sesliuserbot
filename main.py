import os
import sys
import asyncio
import traceback
import random
import json
import re
from threading import Thread
from flask import Flask
from pyrogram import Client, filters, idle
from pyrogram.raw.functions.phone import CreateGroupCall, LeaveGroupCall
from pyrogram.raw.functions.channels import GetFullChannel
from pyrogram.errors import FloodWait, ChatAdminRequired

# --- GÜVENLİK KİLİDİ ---
try:
    sys.set_int_max_str_digits(0)
except Exception:
    pass

# --- FLASK (Railway Keep-Alive) ---
app = Flask(__name__)
@app.route('/')
def home(): 
    return "Bot Aktif - Sistem Çalışıyor"

def run_flask():
    try:
        # Railway PORT değişkenini otomatik atar, yoksa 8080 kullanır
        port = int(os.environ.get("PORT", 8080))
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"❌ Flask Hatası: {e}")

# --- AYARLAR (Environment Variables) ---
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
TARGET_GROUP_ID = int(os.environ.get("TARGET_GROUP_ID", -1003297262036))

# Yönetici ID'leri (Virgülle ayrılmış string olarak alıyoruz)
admin_raw = os.environ.get("ADMIN_IDS", "8416720490,8382929624,652932220,7094870780")
ADMIN_IDS = [int(i.strip()) for i in admin_raw.split(",") if i.strip()]

BANNED_WORDS = ["aramıza", "grubumuza", "grubuna", "sohbet", "ortam", "Haber", "Gündem"]
TELEGRAM_LINK_REGEX = r'(?:https?:\/\/)?(?:t\s*\.\s*me|telegram\s*\.\s*me|telegram\s*\.\s*dog)\s*\/\s*(?:\+)?[\w\-]+'
BLACKLIST_FILE = "blacklist.json"
CMD_PREFIXES = ["/", ".", "!"]

# Botu in_memory=True ile başlatıyoruz (Railway disk çakışmasını önler)
bot = Client(
    "sesli_bot",
    session_string=SESSION_STRING,
    api_id=API_ID,
    api_hash=API_HASH,
    in_memory=True
)

# --- VERİ YÖNETİMİ ---
def load_blacklist():
    if os.path.exists(BLACKLIST_FILE):
        try:
            with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {"7495125802": "Sabıkalı"}

def save_blacklist():
    try:
        with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(BLACKLIST, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ Kayıt hatası: {e}")

BLACKLIST = load_blacklist()

def is_admin(message):
    if not message or not message.from_user: return False
    return message.from_user.is_self or message.from_user.id in ADMIN_IDS

# =========================================================
# 1. SESLİ SOHBET KOMUTLARI
# =========================================================

@bot.on_message(filters.command("sesliac", prefixes=CMD_PREFIXES) & filters.chat(TARGET_GROUP_ID))
async def sesli_ac(client, message):
    try:
        msg = await message.reply("🔄 İşlem başlatılıyor...")
        peer = await client.resolve_peer(message.chat.id)
        full_chat = await client.invoke(GetFullChannel(channel=peer))
        
        if full_chat.full_chat.call:
            await msg.edit("⚠️ Sesli zaten açık.")
            return

        await client.invoke(CreateGroupCall(peer=peer, random_id=random.randint(10000, 99999)))
        await msg.edit("✅ Sesli açıldı. 20s sonra ayrılıyorum.")
        await asyncio.sleep(20)
        
        new_full = await client.invoke(GetFullChannel(channel=peer))
        if new_full.full_chat.call:
            await client.invoke(LeaveGroupCall(call=new_full.full_chat.call, source=0))
    except Exception as e:
        await message.reply(f"❌ Hata: {e}")

# =========================================================
# 2. REKLAM YÖNETİMİ
# =========================================================

@bot.on_message(filters.command("ekle", prefixes=CMD_PREFIXES))
async def add_bl(client, message):
    if not is_admin(message): return
    try:
        target_id = None
        if message.reply_to_message:
            u = message.reply_to_message.from_user
            s = message.reply_to_message.sender_chat
            target_id = str(u.id if u else s.id)
        elif len(message.command) > 1:
            target_id = message.command[1].replace("@", "").lower()
        
        if target_id:
            BLACKLIST[target_id] = "Manuel"
            save_blacklist()
            await message.reply(f"✅ `{target_id}` karalisteye eklendi.")
    except Exception as e: await message.reply(f"Hata: {e}")

@bot.on_message(filters.command("liste", prefixes=CMD_PREFIXES))
async def list_bl(client, message):
    if not is_admin(message): return
    await message.reply(f"📋 **Karaliste:**\n`{list(BLACKLIST.keys())}`")

# =========================================================
# 3. REKLAM SİLİCİ
# =========================================================

@bot.on_message(filters.group, group=1)
async def ad_silici(client, message):
    try:
        if not message.from_user or is_admin(message): return

        sender_id = str(message.from_user.id)
        if sender_id in BLACKLIST or sender_id == "7495125802":
            text = (message.text or message.caption or "").lower()
            if re.search(TELEGRAM_LINK_REGEX, text) or any(w.lower() in text for w in BANNED_WORDS):
                await message.delete()
                print(f"🔥 Reklam Silindi: {sender_id}")
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception:
        pass

# =========================================================
# ANA DÖNGÜ
# =========================================================

async def main():
    # Flask'ı başlat
    Thread(target=run_flask, daemon=True).start()
    
    print("--- BOT BAŞLATILIYOR ---")
    if not API_ID or not API_HASH or not SESSION_STRING:
        print("❌ HATA: Gerekli değişkenler (API_ID, HASH, SESSION) eksik!")
        return

    try:
        await bot.start()
        me = await bot.get_me()
        print(f"✅ Giriş Başarılı: {me.first_name}")
        await idle()
    except Exception as e:
        print(f"🚨 KRİTİK HATA:")
        traceback.print_exc()
    finally:
        if bot.is_connected:
            await bot.stop()
        print("--- BOT DURDURULDU ---")

if __name__ == "__main__":
    asyncio.run(main())
