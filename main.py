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
from pyrogram.errors import FloodWait, ChatAdminRequired

# --- SİSTEM AYARLARI ---
try:
    sys.set_int_max_str_digits(0)
except Exception:
    pass

# --- FLASK (Keep-Alive) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot Aktif - Sistem Çalışıyor"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- AYARLAR VE DEĞİŞKENLER ---
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

# Çoklu Grup ID Sistemi (Virgülle ayrılmış ID'leri listeye çevirir)
target_raw = os.environ.get("TARGET_GROUP_ID", "")
try:
    TARGET_GROUP_IDS = [int(i.strip()) for i in target_raw.split(",") if i.strip()]
except:
    TARGET_GROUP_IDS = []

# Admin Listesi (Railway'den virgülle ayrılmış olarak çekiyoruz)
admin_raw = os.environ.get("ADMIN_IDS", "")
try:
    ADMIN_IDS = [int(i.strip()) for i in admin_raw.split(",") if i.strip()]
except:
    ADMIN_IDS = []

BANNED_WORDS = ["aramıza", "grubumuza", "grubuna", "sohbet", "ortam", "Haber", "Gündem"]
LINK_REGEX = r'(?:https?:\/\/)?(?:t\s*\.\s*me|telegram\s*\.\s*me|telegram\s*\.\s*dog)\s*\/\s*(?:\+)?[\w\-]+'
BLACKLIST_FILE = "blacklist.json"
CMD_PREFIXES = ["/", ".", "!"]

bot = Client("my_userbot", session_string=SESSION_STRING, api_id=API_ID, api_hash=API_HASH, in_memory=True)

# --- VERİ YÖNETİMİ ---
def load_bl():
    if os.path.exists(BLACKLIST_FILE):
        try:
            with open(BLACKLIST_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def save_bl():
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(BLACKLIST, f, ensure_ascii=False, indent=4)

BLACKLIST = load_bl()

def is_admin(message):
    if getattr(message.from_user, "is_self", False): return True
    if not message.from_user: return False
    return message.from_user.id in ADMIN_IDS

# =========================================================
# 1. SESLİ SOHBET KOMUTLARI (GRUPTAKİ HERKESE AÇIK)
# =========================================================

# Dekorator artık TARGET_GROUP_IDS listesini okuyor
@bot.on_message(filters.command(["sesliac", "seslireset"], prefixes=CMD_PREFIXES) & filters.chat(TARGET_GROUP_IDS))
async def voice_manager(client, message):
    # DİKKAT: Burada is_admin kontrolü YOK. Hedef gruptaki herkes kullanabilir.
    cmd = message.command[0].lower()
    
    try:
        msg = await message.reply(f"🔄 İşlem başlatılıyor...")
        peer = await client.resolve_peer(message.chat.id)
        full_chat = await client.invoke(GetFullChannel(channel=peer))
        call_info = full_chat.full_chat.call

        # RESET Komutu: Varsa kapatır
        if cmd == "seslireset" and call_info:
            await msg.edit("🔻 Mevcut sesli sohbet kapatılıyor...")
            await client.invoke(DiscardGroupCall(call=call_info))
            await asyncio.sleep(3)
            call_info = None

        # AC Komutu veya RESET sonrası açma
        if not call_info:
            await msg.edit("🔄 Sesli sohbet açılıyor...")
            await client.invoke(CreateGroupCall(peer=peer, random_id=random.randint(100000, 999999)))
            await msg.edit("✅ Sesli açıldı! 20s sonra ayrılıyorum. Boş yapmaya devam edebilirsiniz.")
        else:
            await msg.edit("⚠️ Sesli zaten açık. Sorun varsa `/seslireset` deneyin.")
            return

        await asyncio.sleep(20)
        
        # Süre dolunca listeden çık
        new_full = await client.invoke(GetFullChannel(channel=peer))
        if new_full.full_chat.call:
            await client.invoke(LeaveGroupCall(call=new_full.full_chat.call, source=0))

    except Exception as e:
        await message.reply(f"❌ Hata: {e}")

# =========================================================
# 2. REKLAM YÖNETİMİ (SADECE ADMİNLERE AÇIK)
# =========================================================

@bot.on_message(filters.command("ekle", prefixes=CMD_PREFIXES) & filters.group)
async def add_blacklist(client, message):
    if not is_admin(message): return
    try:
        target_id = None
        if message.reply_to_message:
            u = message.reply_to_message.from_user
            target_id = str(u.id if u else message.reply_to_message.sender_chat.id)
        elif len(message.command) > 1:
            target_id = message.command[1].replace("@", "").lower()
        
        if target_id:
            BLACKLIST[target_id] = "Banned"
            save_bl()
            await message.reply(f"✅ `{target_id}` karalisteye eklendi.")
        else:
            await message.reply("⚠️ Kimi ekleyeceğimi belirtmedin (ID yaz veya mesaja yanıt ver).")
    except Exception as e: await message.reply(f"Hata: {e}")

@bot.on_message(filters.command("cikar", prefixes=CMD_PREFIXES) & filters.group)
async def remove_blacklist(client, message):
    if not is_admin(message): return
    try:
        target_id = None
        if message.reply_to_message:
            u = message.reply_to_message.from_user
            target_id = str(u.id if u else message.reply_to_message.sender_chat.id)
        elif len(message.command) > 1:
            target_id = message.command[1].replace("@", "").lower()
        
        if target_id and target_id in BLACKLIST:
            del BLACKLIST[target_id]
            save_bl()
            await message.reply(f"✅ `{target_id}` karalisteden **çıkarıldı**.")
        else:
            await message.reply("⚠️ Bu kişi/ID zaten karalistede yok veya ID belirtmedin.")
    except Exception as e: await message.reply(f"Hata: {e}")

@bot.on_message(filters.command("liste", prefixes=CMD_PREFIXES) & filters.group)
async def list_blacklist(client, message):
    if not is_admin(message): return
    if not BLACKLIST:
        await message.reply("📋 Karaliste şu an boş.")
    else:
        await message.reply(f"📋 **Karaliste:**\n`{list(BLACKLIST.keys())}`")

# =========================================================
# 3. OTOMATİK REKLAM SİLİCİ
# =========================================================

@bot.on_message(filters.group, group=1)
async def ad_remover(client, message):
    try:
        if not message.from_user or is_admin(message): return

        sender_id = str(message.from_user.id)
        if sender_id in BLACKLIST or sender_id == "7495125802":
            text = (message.text or message.caption or "").lower()
            if re.search(LINK_REGEX, text) or any(w.lower() in text for w in BANNED_WORDS):
                await message.delete()
    except: pass

# =========================================================
# BAŞLATICI
# =========================================================

async def main():
    Thread(target=run_flask, daemon=True).start()
    print("--- BOT BAŞLATILIYOR ---")
    try:
        await bot.start()
        print(f"✅ Bot Aktif!")
        async for dialog in bot.get_dialogs(): pass
        await idle()
    except Exception as e:
        traceback.print_exc()
    finally:
        if bot.is_connected: await bot.stop()

if __name__ == "__main__":
    # Döngü çakışmalarını önlemek için global event loop kullanıyoruz
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
