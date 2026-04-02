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
from pyrogram.errors import FloodWait, ChatAdminRequired, RPCError

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
        # Railway genelde PORT değişkenini otomatik atar
        port = int(os.environ.get("PORT", 8080))
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"❌ Flask Hatası: {e}")

# --- AYARLAR ---
# Bu değerleri Railway Environment Variables kısmına girin
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
TARGET_GROUP_ID = int(os.environ.get("TARGET_GROUP_ID", -1003297262036))

# Yönetici ID'leri
ADMIN_IDS = [8416720490, 8382929624, 652932220, 7094870780]
BANNED_WORDS = ["aramıza", "grubumuza", "grubuna", "sohbet", "ortam", "Haber", "Gündem"]
TELEGRAM_LINK_REGEX = r'(?:https?:\/\/)?(?:t\s*\.\s*me|telegram\s*\.\s*me|telegram\s*\.\s*dog)\s*\/\s*(?:\+)?[\w\-]+'
BLACKLIST_FILE = "blacklist.json"
CMD_PREFIXES = ["/", ".", "!"]

bot = Client(
    "sesli_bot",
    session_string=SESSION_STRING,
    api_id=API_ID,
    api_hash=API_HASH,
    in_memory=True # Session dosyasını diske yazmaz, güvenlidir
)

# --- VERİ YÖNETİMİ ---
def load_blacklist():
    if os.path.exists(BLACKLIST_FILE):
        try:
            with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Karaliste yükleme hatası: {e}")
            return {}
    return {"7495125802": "Varsayılan Yasaklı"}

def save_blacklist():
    try:
        with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(BLACKLIST, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ Karaliste kaydetme hatası: {e}")

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
        msg = await message.reply("🔄 Sesli Sohbet kontrol ediliyor...")
        peer = await client.resolve_peer(message.chat.id)
        full_chat = await client.invoke(GetFullChannel(channel=peer))
        
        if full_chat.full_chat.call:
            await msg.edit("⚠️ Sesli sohbet zaten açık durumda.")
            return

        await client.invoke(CreateGroupCall(peer=peer, random_id=random.randint(10000, 99999)))
        await msg.edit("✅ Sesli sohbet başarıyla açıldı. 20 saniye sonra gruptan ayrılıyorum.")
        
        await asyncio.sleep(20)
        
        # Yeniden kontrol et ve ayrıl
        new_full = await client.invoke(GetFullChannel(channel=peer))
        if new_full.full_chat.call:
            await client.invoke(LeaveGroupCall(call=new_full.full_chat.call, source=0))
            
    except ChatAdminRequired:
        await message.reply("❌ Hata: Görüntülü sohbet başlatma yetkim yok!")
    except Exception as e:
        await message.reply(f"❌ Teknik Hata: {e}")

# =========================================================
# 2. REKLAM YÖNETİMİ (.ekle / .liste)
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
            BLACKLIST[target_id] = "Manuel Ban"
            save_blacklist()
            await message.reply(f"✅ `{target_id}` başarıyla karalisteye eklendi.")
    except Exception as e: 
        await message.reply(f"❌ Ekleme hatası: {e}")

@bot.on_message(filters.command("liste", prefixes=CMD_PREFIXES))
async def list_bl(client, message):
    if not is_admin(message): return
    ids = list(BLACKLIST.keys())
    if not ids:
        await message.reply("📋 Karaliste şu an boş.")
    else:
        await message.reply(f"📋 **Karaliste:**\n`{', '.join(ids)}`")

# =========================================================
# 3. REKLAM SİLİCİ (GELİŞMİŞ)
# =========================================================

@bot.on_message(filters.group, group=1)
async def ad_silici(client, message):
    try:
        # Mesajı gönderen kişi yoksa veya adminse/botun kendisiyse işlem yapma
        if not message.from_user or is_admin(message):
            return

        sender_id = str(message.from_user.id)
        
        # Sadece karalistekileri denetle
        if sender_id in BLACKLIST or sender_id == "7495125802":
            text = (message.text or message.caption or "").lower()
            
            has_link = bool(re.search(TELEGRAM_LINK_REGEX, text)) or "t.me/" in text
            has_word = any(w.lower() in text for w in BANNED_WORDS)

            if has_link or has_word:
                await message.delete()
                print(f"🔥 Reklam Silindi: {sender_id} | İçerik: {text[:20]}...")
                
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except ChatAdminRequired:
        pass # Yetki yoksa sessizce geç
    except Exception:
        pass

# =========================================================
# BAŞLATMA DÖNGÜSÜ
# =========================================================

async def main():
    # Flask'ı ayrı bir kanalda başlat
    Thread(target=run_flask, daemon=True).start()
    
    print("--- BOT HAZIRLANIYOR ---")
    
    if not API_ID or not API_HASH or not SESSION_STRING:
        print("❌ KRİTİK HATA: API_ID, API_HASH veya SESSION_STRING eksik!")
        return

    try:
        await bot.start()
        me = await bot.get_me()
        print(f"✅ Giriş Başarılı: {me.first_name} (@{me.username})")
        
        # Grup kontrolü
        try:
            chat = await bot.get_chat(TARGET_GROUP_ID)
            print(f"📢 Hedef Grup Aktif: {chat.title}")
        except Exception as e:
            print(f"⚠️ Uyarı: Hedef gruba ulaşılamadı. ID yanlış olabilir veya bot grupta değil.")

        print("--- BOT AKTİF VE DİNLİYOR ---")
        await idle()
        
    except Exception as e:
        print(f"🚨 KRİTİK ÇALIŞMA HATASI:")
        traceback.print_exc()
    finally:
        if bot.is_connected:
            await bot.stop()
        print("--- BOT DURDURULDU ---")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
