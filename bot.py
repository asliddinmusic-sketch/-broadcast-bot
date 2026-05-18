import logging
import json
import os
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    filters,
)

# =============================================
BOT_TOKEN = os.environ.get("8917961411:AAGsjqX71bngb_ee5_wM4q-yzG8uz5Djuuw")
OWNER_ID = int(os.environ.get("OWNER_ID", "1432396874"))
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


def is_owner(update):
    return update.effective_user and update.effective_user.id == OWNER_ID


async def track_chat_member(update, context):
    result = update.my_chat_member
    if not result:
        return
    chat = result.chat
    new_status = result.new_chat_member.status
    chats = load_chats()
    if new_status in ("administrator", "member"):
        chats[str(chat.id)] = {"title": chat.title or "Nomsiz", "type": chat.type, "id": chat.id}
        save_chats(chats)
        logger.info(f"Qoshildi: {chat.title}")
    elif new_status in ("left", "kicked", "restricted"):
        if str(chat.id) in chats:
            del chats[str(chat.id)]
            save_chats(chats)
            logger.info(f"Ochirildi: {chat.title}")


async def start(update, context):
    if not is_owner(update):
        return
    chats = load_chats()
    await update.message.reply_text(
        f"Broadcast Bot faol!\n"
        f"Ulangan: {len(chats)} ta\n\n"
        f"Xabar yuboring - hammaga tarqataman!\n"
        f"/list - royxat\n/status - holat"
    )


async def list_chats(update, context):
    if not is_owner(update):
        return
    chats = load_chats()
    if not chats:
        await update.message.reply_text("Hech narsa yoq. Botni kanal/guruhga admin qiling!")
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
    ch = sum(1 for c in chats.values() if c["type"] == "channel")
    gr = sum(1 for c in chats.values() if c["type"] in ("group", "supergroup"))
    await update.message.reply_text(f"Faol\nKanallar: {ch}\nGuruhlar: {gr}\nJami: {len(chats)}")


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
        await update.message.reply_text("Hech qanday kanal/guruh yoq!")
        return
    sent = 0
    failed = 0
    msg = await update.message.reply_text(f"Yuborilmoqda... 0/{len(chats)}")
    for i, (cid, info) in enumerate(chats.items(), 1):
        try:
            await send_to_chat(context, int(cid), update.message)
            sent += 1
        except Exception as e:
            failed += 1
            logger.warning(f"Xato {info['title']}: {e}")
        if i % 5 == 0 or i == len(chats):
            try:
                await msg.edit_text(f"Yuborilmoqda... {i}/{len(chats)}")
            except Exception:
                pass
    await msg.edit_text(f"Tugadi! Yuborildi: {sent} | Xato: {failed}")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_chats))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(ChatMemberHandler(track_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, broadcast))
    logger.info("Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
