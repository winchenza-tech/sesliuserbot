import os
import asyncio # Zamanlama için gerekli
from threading import Thread
from flask import Flask
from pyrogram import Client, filters
from pyrogram.raw.functions.phone import CreateGroupCall, LeaveGroupCall
from pyrogram.raw.functions.messages import GetFullChat




@bot.on_message(filters.command("sesliac") & filters.group)
async def start_and_leave_voice(client, message):
    try:
        # 1. Sesli sohbeti başlat
        peer = await client.resolve_peer(message.chat.id)
        await client.invoke(
            CreateGroupCall(
                peer=peer,
                random_id=client.rnd_id()
            )
        )
        await message.reply("✅ Sesli sohbet başlatıldı! 10 saniye sonra ayrılacağım.")

        # 2. 10 saniye bekle
        await asyncio.sleep(10)

        # 3. Aktif sesli sohbetin ID'sini bulmak için grup bilgisini çek
        full_chat = await client.invoke(GetFullChat(peer=peer))
        call_info = full_chat.full_chat.call # Aktif çağrı bilgisi

        if call_info:
            # 4. Sesli sohbetten ayrıl
            await client.invoke(
                LeaveGroupCall(
                    call=call_info,
                    source=0 # Standart kaynak değeri
                )
            )
            print(f"{message.chat.title} grubundaki sesli sohbetten ayrılındı.")
        else:
            print("Ayrılmak için aktif bir sesli sohbet bulunamadı.")

    except Exception as e:
        await message.reply(f"❌ Hata: {e}")

