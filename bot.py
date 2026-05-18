import logging
import json
import os
import asyncio
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    filters,
)

# =============================================
BOT_TOKEN = "8917961411:AAGsjqX71bngb_ee5_wM4q-yzG8uz5Djuuw"
OWNER_ID = 1432396874
CHATS_FILE = "chats.json"
# =============================================

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


def load_chats():
    if os.path.exists(CHATS_FILE):
        with open(CHATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_chats(chats):
    with open(CHATS_FILE, "w", encoding="utf-8") as f:
        json.dump(chats, f, ensure_ascii=False, indent=2)


def add_chat(chat_id, title, chat_type):
    chats = load_chats()
    chats[str(chat_id)] = {"title": title, "type": chat_type, "id": chat_id}
    save_chats(chats)
    logger.info(f"Qoshildi: {title} ({chat_id})")


def remove_chat(chat_id):
    chats = load_chats()
    if str(chat_id) in chats:
        del chats[str(chat_id)]
        save_chats(chats)


def is_owner(update):
    return update.effective_user and update.effective_user.id == OWNER_ID


async def track_chat_member(update, context):
    result = update.my_chat_member
    if not result:
        return
    chat = result.chat
    new_status = result.new_chat_member.status
    if new_status in ("administrator", "member"):
        add_chat(chat.id, chat.title or "Nomsiz", chat.type)
    elif new_status in ("left", "kicked", "restricted"):
        remove_chat(chat.id)


async def start(update, context):
    if not is_owner(update):
        return
    chats = load_chats()
    await update.message.reply_text(
        f"Broadcast Bot faol!\n\n"
        f"Ulangan: {len(chats)} ta kanal/guruh\n\n"
        f"Xabar yuboring - hammaga tarqataman!\n"
        f"/list - royxat\n"
        f"/status - holat"
    )


async def list_chats(update, context):
    if not is_owner(update):
        return
    chats = load_chats()
    if not chats:
        await update.message.reply_text("Hech qanday kanal/guruh yoq.\nBotni admin qiling!")
        return
    text = f"Jami: {len(chats)} ta\n\n"
    for c in chats.values():
        tip = "Kanal" if c["type"] == "channel" else "Guruh"
        text += f"{tip}: {c['title']}\n"
    await update.message.reply_text(text)


async def status_cmd(update, context):
    if not is_owner(update):
        return
    chats = load_chats()
    channels = sum(1 for c in chats.values() if c["type"] == "channel")
    groups = sum(1 for c in chats.values() if c["type"] in ("group", "supergroup"))
    await update.message.reply_text(
        f"Bot: Faol\nKanallar: {channels} ta\nGuruhlar: {groups} ta\nJami: {len(chats)} ta"
    )


async def send_to_chat(context, chat_id, message):
    if message.text:
        await context.bot.send_message(chat_id=chat_id, text=message.text)
    elif message.photo:
        await context.bot.send_photo(chat_id=chat_id, photo=message.photo[-1].file_id, caption=message.caption or "")
    elif message.video:
        await context.bot.send_video(chat_id=chat_id, video=message.video.file_id, caption=message.caption or "")
    elif message.audio:
        await context.bot.send_audio(chat_id=chat_id, audio=message.audio.file_id, caption=message.caption or "")
    elif message.voice:
        await context.bot.send_voice(chat_id=chat_id, voice=message.voice.file_id)
    elif message.document:
        await context.bot.send_document(chat_id=chat_id, document=message.document.file_id, caption=message.caption or "")
    elif message.sticker:
        await context.bot.send_sticker(chat_id=chat_id, sticker=message.sticker.file_id)
    elif message.animation:
        await context.bot.send_animation(chat_id=chat_id, animation=message.animation.file_id, caption=message.caption or "")
    elif message.video_note:
        await context.bot.send_video_note(chat_id=chat_id, video_note=message.video_note.file_id)


async def broadcast(update, context):
    if not is_owner(update):
        return
    chats = load_chats()
    if not chats:
        await update.message.reply_text("Hech qanday kanal/guruh yoq! Avval botni admin qiling.")
        return

    sent = 0
    failed = 0
    status_msg = await update.message.reply_text(f"Yuborilmoqda... 0/{len(chats)}")

    for i, (chat_id_str, chat_info) in enumerate(chats.items(), 1):
        try:
            await send_to_chat(context, int(chat_id_str), update.message)
            sent += 1
        except Exception as e:
            failed += 1
            logger.warning(f"Xato {chat_info['title']}: {e}")
            if "kicked" in str(e).lower() or "not found" in str(e).lower():
                remove_chat(int(chat_id_str))
        if i % 3 == 0 or i == len(chats):
            try:
                await status_msg.edit_text(f"Yuborilmoqda... {i}/{len(chats)}")
            except Exception:
                pass

    await status_msg.edit_text(f"Tugadi!\nYuborildi: {sent} ta\nXato: {failed} ta")


async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_chats))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(ChatMemberHandler(track_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, broadcast))

    logger.info("Broadcast Bot ishga tushdi!")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
