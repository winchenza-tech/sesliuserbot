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

bot = Client("sesli_bot", session_string=SESSION_STRING, api_id=API_ID, api_hash=API_HASH)

# --- AYARLAR (Reklam Engelleyici) ---
ADMIN_IDS = [8416720490, 8382929624, 652932220, 7094870780] 
BANNED_WORDS = ["aramıza", "grubumuza", "grubuna", "sohbet", "ortam"]
TELEGRAM_LINK_REGEX = r'(?:https?:\/\/)?(?:t\s*\.\s*me|telegram\s*\.\s*me|telegram\s*\.\s*dog)\s*\/\s*(?:\+)?[\w\-]+'
BLACKLIST_FILE = "blacklist.json"
CMD_PREFIXES = ["/", ".", "!"] 

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

def is_admin(user):
    if not user: return False
    return user.is_self or (user.id in ADMIN_IDS)


# =========================================================
# 1. SESLİ SOHBET KOMUTLARI (SADECE HEDEF GRUPTA ÇALIŞIR)
# =========================================================

@bot.on_message(filters.command("sesliac", prefixes=CMD_PREFIXES) & filters.group)
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

@bot.on_message(filters.command("seslireset", prefixes=CMD_PREFIXES) & filters.group)
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
# 2. REKLAM YÖNETİM KOMUTLARI (.ekle / .cikar / .liste)
# =========================================================

@bot.on_message(filters.command("ekle", prefixes=CMD_PREFIXES) & filters.group)
async def add_blacklist_command(client, message):
    try:
        if not is_admin(message.from_user): return

        if message.reply_to_message and message.reply_to_message.from_user:
            target_user = message.reply_to_message.from_user
            target_id = str(target_user.id)
            
            BLACKLIST[target_id] = f"ID Ban (Ekleyen: {message.from_user.first_name})"
            if target_user.username:
                BLACKLIST[target_user.username.lower()] = f"Username Ban (Ekleyen: {message.from_user.first_name})"
            
            save_blacklist()
            await message.reply(f"✅ Kullanıcı karalisteye eklendi (ID: {target_id}).")
            return

        if len(message.command) > 1:
            target = message.command[1].replace("@", "").lower()
            BLACKLIST[target] = f"Manuel Eklendi (Ekleyen: {message.from_user.first_name})"
            save_blacklist()
            await message.reply(f"✅ `{target}` karalisteye eklendi.")
        else:
            await message.reply("⚠️ Kullanım: Bir mesaja yanıt verin veya `.ekle <id_veya_username>` yazın.")
    except Exception as e:
        await message.reply(f"❌ Komut Hatası: {e}")

@bot.on_message(filters.command("cikar", prefixes=CMD_PREFIXES) & filters.group)
async def remove_blacklist_command(client, message):
    try:
        if not is_admin(message.from_user): return

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
            await message.reply("⚠️ Kullanım: Bir mesaja yanıt verin veya `.cikar <id_veya_username>` yazın.")
    except Exception as e:
        await message.reply(f"❌ Komut Hatası: {e}")

@bot.on_message(filters.command("liste", prefixes=CMD_PREFIXES) & filters.group)
async def list_blacklist_command(client, message):
    if not is_admin(message.from_user): return
    
    if not BLACKLIST:
        await message.reply("📋 Karaliste şu an boş.")
        return

    text = "📋 **Güncel Karaliste:**\n"
    for key, value in BLACKLIST.items():
        text += f"• `{key}` - _{value}_\n"
    
    await message.reply(text)


# =========================================================
# 3. REKLAM DENETLEYİCİ (TÜM GRUPLAR İÇİN DERİN X-RAY)
# =========================================================

@bot.on_message(filters.group, group=1)
async def delete_octopus_ads(client, message):
    # Sadece hedef grupta (-1003297262036) veya sabıkalı hesaptan gelirse detaylı log basalım
    is_target_group = (message.chat.id == -1003297262036)
    
    if is_target_group:
        print("\n" + "="*50)
        print(f"📥 [YENİ MESAJ] Grup ID: {message.chat.id}")

    user_id_str = ""
    username = ""
    is_admin_flag = False

    # 1. MESAJ KİMDEN GELDİ?
    if not message.from_user:
        if is_target_group: print("⚠️ 'from_user' bilgisi YOK! (Mesaj kanal veya anonim yönetici olarak atılmış)")
        
        # Gönderen kanal/grup ID'sini yakalamaya çalışalım
        if message.sender_chat:
            user_id_str = str(message.sender_chat.id)
            username = message.sender_chat.username.lower() if message.sender_chat.username else ""
            if is_target_group: print(f"👤 Gönderen Kanal/Grup ID: {user_id_str} | Username: {username}")
        else:
            if is_target_group: print("❌ Gönderen bilgisi tamamen gizli. Pas geçiliyor.\n" + "="*50)
            return
    else:
        user_id_str = str(message.from_user.id)
        username = message.from_user.username.lower() if message.from_user.username else ""
        is_admin_flag = is_admin(message.from_user)
        if is_target_group: print(f"👤 Gönderen Kullanıcı ID: {user_id_str} | Username: {username}")

    # 2. ADMİN KONTROLÜ
    if is_admin_flag:
        if is_target_group: print("🛡️ Bu kişi yetkili/admin. Pas geçiliyor.\n" + "="*50)
        return

    # 3. KARALİSTE KONTROLÜ
    is_test_account = (user_id_str == "7495125802")
    is_blacklisted = (username in BLACKLIST) or (user_id_str in BLACKLIST) or is_test_account
    
    if is_target_group: print(f"🔍 Karalistede mi?: {is_blacklisted} | Hedef 7495125802 mi?: {is_test_account}")

    if not is_blacklisted:
        if is_target_group: print("✅ Hesap sabıkalı değil, mesaja dokunulmadı.\n" + "="*50)
        return

    # 4. İÇERİK KONTROLÜ
    content = message.text or message.caption or ""
    content_lower = content.lower()
    
    if is_target_group: print(f"📝 İçerik Önizleme: {content[:30]}...")

    has_link = bool(re.search(TELEGRAM_LINK_REGEX, content, re.IGNORECASE | re.MULTILINE))
    has_banned_word = any(word in content_lower for word in BANNED_WORDS)

    # GÜVENLİK AĞI
    if not has_link and ("t.me/" in content_lower or "telegram.me/" in content_lower):
        has_link = True
        if is_target_group: print("-> Regex kaçırdı ama düz metinde t.me bulundu!")

    if is_target_group: print(f"🔗 Link var mı?: {has_link} | 🤬 Yasaklı kelime var mı?: {has_banned_word}")

    # 5. SİLME İŞLEMİ
    if has_link or has_banned_word:
        try:
            await message.delete()
            print(f"🚀 BAŞARILI: REKLAM SİLİNDİ! Grup: {message.chat.id} | Gönderen: {user_id_str}")
        except Exception as e:
            print(f"❌ SİLME HATASI! Yetki kontrolü yap. Detay: {e}")
    else:
        if is_target_group: print("🟢 temizz.")
        
    if is_target_group: print("="*50 + "\n")


# =========================================================
# BAŞLATMA
# =========================================================

async def main():
    Thread(target=run_flask).start()
    print("Bot başlatılıyor...")
    await bot.start()
    
    async for dialog in bot.get_dialogs(): pass
    
    print("🚀 Bot hazır!")
    print("NOT: Komutları /ekle yerine .ekle veya !ekle olarak da kullanabilirsiniz.")
    await idle()
    await bot.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
