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

# --- GÜVENLİK KİLİDİNİ KALDIR ---
try:
    sys.set_int_max_str_digits(0)
except Exception:
    pass

# --- FLASK (Web Server) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot Aktif ve Reklam Avında!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- AYARLAR (Userbot & Sesli) ---
try:
    API_ID = int(os.environ.get("API_ID", "0").strip())
    API_HASH = os.environ.get("API_HASH", "").strip()
    SESSION_STRING = os.environ.get("SESSION_STRING", "").strip()
    TARGET_GROUP_ID = int(os.environ.get("TARGET_GROUP_ID", "0").strip())
except Exception as e:
    print(f"Ayar Hatası: {e}")
    # Local'de test ediyorsan programın kapanmaması için exit(1) kaldırılabilir.

bot = Client("sesli_bot", session_string=SESSION_STRING, api_id=API_ID, api_hash=API_HASH)

# --- AYARLAR (Reklam Engelleyici) ---
# Kendi ID'ni veya yetki vermek istediğin kişilerin ID'lerini buraya ekle
ADMIN_IDS = [8416720490, 8382929624, 652932220, 7094870780] 
BANNED_WORDS = ["aramıza", "grubumuza", "grubuna", "sohbet", "ortam"]
TELEGRAM_LINK_REGEX = r'(?:https?:\/\/)?(?:t\s*\.\s*me|telegram\s*\.\s*me|telegram\s*\.\s*dog)\s*\/\s*(?:\+)?[\w\-]+'
BLACKLIST_FILE = "blacklist.json"

# --- JSON VERİTABANI İŞLEMLERİ ---
def load_blacklist():
    default_blacklist = {
        "octopusgame_bot": "Octopus Game TR Reklam Botu",
        "silinenyesil": "Deneme Test Hesabı"
    }
    if os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                data.update(default_blacklist)
                return data
            except:
                return default_blacklist
    return default_blacklist

def save_blacklist():
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(BLACKLIST, f, ensure_ascii=False, indent=4)

BLACKLIST = load_blacklist()

def is_admin(user_id):
    return user_id in ADMIN_IDS

# =========================================================
# 1. SESLİ SOHBET KOMUTLARI (SADECE HEDEF GRUPTA ÇALIŞIR)
# =========================================================

@bot.on_message(filters.command("sesliac") & filters.group)
async def sesli_ac(client, message):
    if message.chat.id != TARGET_GROUP_ID: return

    try:
        msg = await message.reply("🔍 Kontrol ediliyor...")
        peer = await client.resolve_peer(message.chat.id)
        
        full_chat = await client.invoke(GetFullChannel(channel=peer))
        existing_call = full_chat.full_chat.call

        if existing_call:
            await msg.edit("⚠️ **Sesli sohbet zaten açık.**\nEğer hala sorun yaşıyorsan `/seslireset` yazabilirsin. Sorun devam ederse Zenithar'ı etiketleyin.")
            return
        
        await msg.edit("🔄 Sesli sohbet başlatılıyor...")
        await client.invoke(CreateGroupCall(peer=peer, random_id=random.randint(100000, 999999)))
        await msg.edit("✅ Sesli sohbet açıldı! 20 saniye sonra listeden çıkacağım.")
        
        await asyncio.sleep(20)
        
        full_chat_new = await client.invoke(GetFullChannel(channel=peer))
        call_info = full_chat_new.full_chat.call
        
        if call_info:
            await client.invoke(LeaveGroupCall(call=call_info, source=0))
            await msg.edit("✅ Sesli sohbet açıldı. Doluşun")
        
    except Exception as e:
        await message.reply(f"❌ Hata: {e}")

@bot.on_message(filters.command("seslireset") & filters.group)
async def sesli_reset(client, message):
    if message.chat.id != TARGET_GROUP_ID: return

    try:
        msg = await message.reply("🔄 Sesli sohbet SIFIRLANIYOR...")
        peer = await client.resolve_peer(message.chat.id)

        full_chat = await client.invoke(GetFullChannel(channel=peer))
        call_info = full_chat.full_chat.call

        if call_info:
            await msg.edit("🔻 Mevcut sesli sohbet kapatılıyor...")
            await client.invoke(DiscardGroupCall(call=call_info))
            await asyncio.sleep(3)
        else:
            await msg.edit("ℹ️ Zaten açık bir sohbet yok, yenisi açılıyor...")

        await client.invoke(CreateGroupCall(peer=peer, random_id=random.randint(100000, 999999)))
        await msg.edit("✅ Yeni sesli sohbet açıldı! 20 saniye sonra çıkacağım.")

        await asyncio.sleep(20)

        full_chat_new = await client.invoke(GetFullChannel(channel=peer))
        new_call_info = full_chat_new.full_chat.call

        if new_call_info:
            await client.invoke(LeaveGroupCall(call=new_call_info, source=0))
            await msg.edit("✅ İşlem tamamlandı. (Bot ayrıldı)")
        
    except Exception:
        error_trace = traceback.format_exc()
        if len(error_trace) > 4000: error_trace = error_trace[:4000]
        await message.reply(f"❌ **HATA:**\n`{error_trace}`")


# =========================================================
# 2. REKLAM YÖNETİM KOMUTLARI (TÜM GRUPLARDA ÇALIŞIR)
# =========================================================

@bot.on_message(filters.command("ekle") & filters.group)
async def add_blacklist_command(client, message):
    if not message.from_user or not is_admin(message.from_user.id): return

    # Yanıtlanan mesaj varsa
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
        target_id = str(target_user.id)
        
        BLACKLIST[target_id] = f"ID Ban (Ekleyen: {message.from_user.first_name})"
        if target_user.username:
            BLACKLIST[target_user.username.lower()] = f"Username Ban (Ekleyen: {message.from_user.first_name})"
        
        save_blacklist()
        await message.reply(f"✅ Kullanıcı karalisteye eklendi (ID: {target_id}).")
        return

    # Argüman girilmişse
    if len(message.command) > 1:
        target = message.command[1].replace("@", "").lower()
        BLACKLIST[target] = f"Manuel Eklendi (Ekleyen: {message.from_user.first_name})"
        save_blacklist()
        await message.reply(f"✅ `{target}` karalisteye eklendi.")
    else:
        await message.reply("Kullanım: Bir mesaja yanıt verin veya `/ekle <id_veya_username>` yazın.")

@bot.on_message(filters.command("cikar") & filters.group)
async def remove_blacklist_command(client, message):
    if not message.from_user or not is_admin(message.from_user.id): return

    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
        target_id = str(target_user.id)
        target_username = target_user.username.lower() if target_user.username else None
        
        removed = False
        if target_id in BLACKLIST:
            del BLACKLIST[target_id]
            removed = True
        if target_username and target_username in BLACKLIST:
            del BLACKLIST[target_username]
            removed = True
            
        if removed:
            save_blacklist()
            await message.reply("✅ Kullanıcı karalisteden çıkarıldı.")
        else:
            await message.reply("⚠️ Bu kullanıcı zaten karalistede bulunmuyor.")
        return

    if len(message.command) > 1:
        target = message.command[1].replace("@", "").lower()
        if target in BLACKLIST:
            del BLACKLIST[target]
            save_blacklist()
            await message.reply(f"✅ `{target}` karalisteden çıkarıldı.")
        else:
            await message.reply(f"⚠️ `{target}` karalistede bulunamadı.")
    else:
        await message.reply("Kullanım: Bir mesaja yanıt verin veya `/cikar <id_veya_username>` yazın.")

@bot.on_message(filters.command("liste") & filters.group)
async def list_blacklist_command(client, message):
    if not message.from_user or not is_admin(message.from_user.id): return
    
    if not BLACKLIST:
        await message.reply("📋 Karaliste şu an boş.")
        return

    text = "📋 **Güncel Karaliste:**\n"
    for key, value in BLACKLIST.items():
        text += f"• `{key}` - _{value}_\n"
    
    await message.reply(text)


# =========================================================
# 3. REKLAM DENETLEYİCİ (TÜM GRUPLARDA SADECE KARALİSTEYİ TARAR)
# =========================================================

@bot.on_message(filters.group, group=1)
async def delete_octopus_ads(client, message):
    if not message.from_user: return
    
    # Yönetici ise pas geç
    if is_admin(message.from_user.id): return

    username = message.from_user.username.lower() if message.from_user.username else ""
    user_id_str = str(message.from_user.id)
    
    # 1. KONTROL: Bu kişi karalistede mi?
    is_blacklisted = (username in BLACKLIST) or (user_id_str in BLACKLIST)
    
    # EĞER KARALİSTEDE DEĞİLSE MESAJA HİÇ BAKMADAN ÇIK
    if not is_blacklisted:
        return

    # 2. KONTROL: Karalistedeki kişi mesaj atmış, içinde reklam var mı?
    content = message.text or message.caption or ""
    content_lower = content.lower()

    has_link = bool(re.search(TELEGRAM_LINK_REGEX, content, re.IGNORECASE | re.MULTILINE))
    has_banned_word = any(word in content_lower for word in BANNED_WORDS)

    # Karalistedeki kişinin mesajında link veya yasaklı kelime varsa sil
    if has_link or has_banned_word:
        try:
            await message.delete()
            
            yakalanan_sey = []
            if has_link: yakalanan_sey.append("Link")
            if has_banned_word: yakalanan_sey.append("Yasaklı Kelime")
            
            sebep = f"Karaliste ({user_id_str}/{username}) -> {' + '.join(yakalanan_sey)}"
            print(f"✅ REKLAM SİLİNDİ: {message.from_user.first_name} (@{username}) | Sebep: {sebep}")
            
        except Exception as e:
            print(f"❌ Silme hatası: {e} - Botun bulunduğu grupta mesaj silme yetkisi olmayabilir.")


# =========================================================
# BAŞLATMA
# =========================================================

async def main():
    Thread(target=run_flask).start()
    print("Bot başlatılıyor...")
    await bot.start()
    
    # Dialogları güncellemek (ID hatalarını önler)
    async for dialog in bot.get_dialogs(): pass
    
    print("🚀 Bot hazır, sesli komutları ve tüm gruplarda karaliste denetimi aktif!")
    await idle()
    await bot.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
