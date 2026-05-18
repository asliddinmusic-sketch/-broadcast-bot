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
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8917961411:AAGsjqX71bngb_ee5_wM4q-yzG8uz5Djuuw")
OWNER_IDS = [int(x) for x in os.environ.get("OWNER_ID", "1432396874").split(",")]
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
    return update.effective_user and update.effective_user.id in OWNER_IDS


def get_message_link(chat_id, message_id, username=None):
    """Xabar havolasini olish"""
    if username:
        return f"https://t.me/{username}/{message_id}"
    else:
        # Private kanal/guruh uchun (chat_id dan -100 ni olib tashlash)
        clean_id = str(chat_id).replace("-100", "")
        return f"https://t.me/c/{clean_id}/{message_id}"


async def track_chat_member(update, context):
    result = update.my_chat_member
    if not result:
        return
    chat = result.chat
    new_status = result.new_chat_member.status
    chats = load_chats()
    if new_status in ("administrator", "member"):
        chats[str(chat.id)] = {
            "title": chat.title or "Nomsiz",
            "type": chat.type,
            "id": chat.id,
            "username": chat.username or None
        }
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
    """Xabar yuborish va yuborilgan xabarni qaytarish"""
    if message.text:
        return await context.bot.send_message(chat_id=chat_id, text=message.text)
    elif message.photo:
        return await context.bot.send_photo(chat_id=chat_id, photo=message.photo[-1].file_id, caption=message.caption or "")
    elif message.video:
        return await context.bot.send_video(chat_id=chat_id, video=message.video.file_id, caption=message.caption or "")
    elif message.audio:
        return await context.bot.send_audio(chat_id=chat_id, audio=message.audio.file_id, caption=message.caption or "")
    elif message.voice:
        return await context.bot.send_voice(chat_id=chat_id, voice=message.voice.file_id)
    elif message.document:
        return await context.bot.send_document(chat_id=chat_id, document=message.document.file_id, caption=message.caption or "")
    elif message.sticker:
        return await context.bot.send_sticker(chat_id=chat_id, sticker=message.sticker.file_id)
    elif message.animation:
        return await context.bot.send_animation(chat_id=chat_id, animation=message.animation.file_id, caption=message.caption or "")
    elif message.video_note:
        return await context.bot.send_video_note(chat_id=chat_id, video_note=message.video_note.file_id)


async def broadcast(update, context):
    if not is_owner(update):
        return
    chats = load_chats()
    if not chats:
        await update.message.reply_text("Hech qanday kanal/guruh yoq!")
        return

    sent = 0
    failed = 0
    links = []

    status_msg = await update.message.reply_text(f"Yuborilmoqda... 0/{len(chats)}")

    for i, (cid, info) in enumerate(chats.items(), 1):
        try:
            sent_msg = await send_to_chat(context, int(cid), update.message)
            sent += 1

            # Havola olish
            if sent_msg:
                tip = "Kanal" if info["type"] == "channel" else "Guruh"
                link = get_message_link(
                    chat_id=int(cid),
                    message_id=sent_msg.message_id,
                    username=info.get("username")
                )
                links.append(f"{tip} — {info['title']}:\n{link}")

        except Exception as e:
            failed += 1
            logger.warning(f"Xato {info['title']}: {e}")

        if i % 5 == 0 or i == len(chats):
            try:
                await status_msg.edit_text(f"Yuborilmoqda... {i}/{len(chats)}")
            except Exception:
                pass

    # Natija xabari
    result = f"✅ Tugadi!\nYuborildi: {sent} ta | Xato: {failed} ta\n\n"

    if links:
        result += "🔗 Havolalar:\n\n" + "\n\n".join(links)

    # Agar xabar juda uzun bo'lsa, bo'laklarga bo'lish
    if len(result) > 4000:
        await status_msg.edit_text(f"✅ Tugadi!\nYuborildi: {sent} ta | Xato: {failed} ta")
        # Havolalarni alohida yuborish
        chunk = "🔗 Havolalar:\n\n"
        for link in links:
            if len(chunk) + len(link) > 4000:
                await update.message.reply_text(chunk)
                chunk = ""
            chunk += link + "\n\n"
        if chunk:
            await update.message.reply_text(chunk)
    else:
        await status_msg.edit_text(result)


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
