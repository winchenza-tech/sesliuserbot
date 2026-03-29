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
from pyrogram.raw.functions.phone import CreateGroupCall, LeaveGroupCall, DiscardGroupCall
from pyrogram.raw.functions.channels import GetFullChannel
from pyrogram.errors import FloodWait, ChatAdminRequired, UserPrivacyRestricted

# --- GÜVENLİK KİLİDİ ---
try:
    sys.set_int_max_str_digits(0)
except Exception:
    pass

# --- FLASK (Railway Keep-Alive) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot Aktif"

def run_flask():
    try:
        port = int(os.environ.get("PORT", 8080))
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"Flask Hatası: {e}")

# --- AYARLAR ---
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
TARGET_GROUP_ID = int(os.environ.get("TARGET_GROUP_ID", "-1003297262036"))

bot = Client("sesli_bot", session_string=SESSION_STRING, api_id=API_ID, api_hash=API_HASH)

# Karaliste ve Adminler
ADMIN_IDS = [8416720490, 8382929624, 652932220, 7094870780]
BANNED_WORDS = ["aramıza", "grubumuza", "grubuna", "sohbet", "ortam", "Haber", "Gündem"]
TELEGRAM_LINK_REGEX = r'(?:https?:\/\/)?(?:t\s*\.\s*me|telegram\s*\.\s*me|telegram\s*\.\s*dog)\s*\/\s*(?:\+)?[\w\-]+'
BLACKLIST_FILE = "blacklist.json"
CMD_PREFIXES = ["/", ".", "!"]

# --- VERİ YÖNETİMİ ---
def load_blacklist():
    if os.path.exists(BLACKLIST_FILE):
        try:
            with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {"7495125802": "Sabıkalı Test Hesabı"}

def save_blacklist():
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(BLACKLIST, f, ensure_ascii=False, indent=4)

BLACKLIST = load_blacklist()

def is_admin(message):
    if not message.from_user: return False
    return message.from_user.is_self or message.from_user.id in ADMIN_IDS

# =========================================================
# 1. SESLİ SOHBET KOMUTLARI
# =========================================================

@bot.on_message(filters.command("sesliac", prefixes=CMD_PREFIXES) & filters.chat(TARGET_GROUP_ID))
async def sesli_ac(client, message):
    try:
        msg = await message.reply("🔄 İşleniyor...")
        peer = await client.resolve_peer(message.chat.id)
        full_chat = await client.invoke(GetFullChannel(channel=peer))
        
        if full_chat.full_chat.call:
            await msg.edit("⚠️ Sesli zaten açık.")
            return

        await client.invoke(CreateGroupCall(peer=peer, random_id=random.randint(10000, 99999)))
        await msg.edit("✅ Sesli açıldı. 20s sonra ayrılıyorum.")
        await asyncio.sleep(20)
        
        # Ayrılma
        new_full = await client.invoke(GetFullChannel(channel=peer))
        if new_full.full_chat.call:
            await client.invoke(LeaveGroupCall(call=new_full.full_chat.call, source=0))
    except Exception as e:
        await message.reply(f"❌ Hata: {e}")

# =========================================================
# 2. REKLAM YÖNETİMİ (.ekle / .cikar)
# =========================================================

@bot.on_message(filters.command("ekle", prefixes=CMD_PREFIXES))
async def add_bl(client, message):
    if not is_admin(message): return
    try:
        target_id = None
        if message.reply_to_message:
            target_id = str(message.reply_to_message.from_user.id if message.reply_to_message.from_user else message.reply_to_message.sender_chat.id)
        elif len(message.command) > 1:
            target_id = message.command[1].replace("@", "").lower()
        
        if target_id:
            BLACKLIST[target_id] = "Manuel Ban"
            save_blacklist()
            await message.reply(f"✅ `{target_id}` listeye eklendi.")
    except Exception as e: await message.reply(f"Hata: {e}")

@bot.on_message(filters.command("liste", prefixes=CMD_PREFIXES))
async def list_bl(client, message):
    if not is_admin(message): return
    await message.reply(f"📋 **Karaliste:**\n`{list(BLACKLIST.keys())}`")

# =========================================================
# 3. ANA REKLAM SİLİCİ (TÜM GRUPLAR + KANAL MESAJLARI)
# =========================================================

@bot.on_message(filters.group, group=1)
async def ad_silici(client, message):
    try:
        # Adminse dokunma
        if is_admin(message): return

        # Gönderen ID tespiti (Kullanıcı veya Kanal)
        sender_id = None
        if message.from_user:
            sender_id = str(message.from_user.id)
        elif message.sender_chat:
            sender_id = str(message.sender_chat.id)
        
        if not sender_id: return

        # Karaliste veya Özel Hedef Kontrolü
        is_bad = (sender_id in BLACKLIST) or (sender_id == "7495125802")
        
        if is_bad:
            text = (message.text or message.caption or "").lower()
            has_link = bool(re.search(TELEGRAM_LINK_REGEX, text)) or "t.me/" in text
            has_word = any(w.lower() in text for w in BANNED_WORDS)

            if has_link or has_word:
                await message.delete()
                print(f"🔥 Reklam Silindi: {sender_id}")
                
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except ChatAdminRequired:
        print(f"❌ Yetki Hatası: {message.chat.id} grubunda yönetici değilim!")
    except Exception:
        pass

# =========================================================
# BAŞLATMA
# =========================================================

async def main():
    Thread(target=run_flask, daemon=True).start()
    print("--- BOT BAŞLATILIYOR ---")
    try:
        await bot.start()
        # Botun kendi bilgisini al
        me = await bot.get_me()
        print(f"✅ Giriş Yapıldı: {me.first_name} (@{me.username})")
        
        # Gruba erişimi doğrula
        try:
            await bot.get_chat(TARGET_GROUP_ID)
            print(f"📢 Hedef Grup ({TARGET_GROUP_ID}) Erişilebilir.")
        except:
            print(f"⚠️ UYARI: Hedef gruba erişilemiyor! ID yanlış veya bot grupta değil.")

        await idle()
    except Exception as e:
        print(f"KRİTİK HATA: {e}")
    finally:
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
