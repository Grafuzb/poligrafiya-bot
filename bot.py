import logging
import os
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
import gspread
from google.oauth2.service_account import Credentials

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8940240035:AAHtzUFhXPvtzfidIQ7GfhcADPcEu9mAPPU"
SPREADSHEET_ID = "1QaynFT9_9rPb7ycQV3t9ZMvedTGYgq6ulf-bCewuLJk"
DIRECTOR_CHAT_ID = "389839743"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_sheet():
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    return sheet

MIJOZ, BUYURTMA, SUMMA, IZOH = range(4)
TOLANDI_MIJOZ = range(4, 5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["/yangi", "/tolandi"],
        ["/royxat", "/hisobot"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Salom! Poligrafiya qarz boti.\n\n"
        "/yangi — yangi qarz kiritish\n"
        "/tolandi — to'lov qilindi\n"
        "/royxat — barcha qarzlar\n"
        "/hisobot — haftalik hisobot",
        reply_markup=reply_markup
    )

async def yangi_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Mijoz ismini kiriting:",
        reply_markup=ReplyKeyboardRemove()
    )
    return MIJOZ

async def yangi_mijoz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mijoz"] = update.message.text
    keyboard = [["Vizitka", "Banner"], ["Kitob", "Buklet"], ["Boshqa"]]
    await update.message.reply_text(
        "Buyurtma turini tanlang:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return BUYURTMA

async def yangi_buyurtma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["buyurtma"] = update.message.text
    await update.message.reply_text(
        "Qarz summasini kiriting (so'm):",
        reply_markup=ReplyKeyboardRemove()
    )
    return SUMMA

async def yangi_summa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        summa = int(update.message.text.replace(" ", "").replace(",", ""))
        context.user_data["summa"] = summa
    except ValueError:
        await update.message.reply_text("Iltimos, faqat raqam kiriting:")
        return SUMMA
    await update.message.reply_text("Izoh kiriting (yoki - yozing):")
    return IZOH

async def yangi_izoh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    izoh = update.message.text
    if izoh == "-":
        izoh = ""
    
    mijoz = context.user_data["mijoz"]
    buyurtma = context.user_data["buyurtma"]
    summa = context.user_data["summa"]
    sana = datetime.now().strftime("%d.%m.%Y")
    
    try:
        sheet = get_sheet()
        sheet.append_row([mijoz, buyurtma, summa, sana, "To'lanmagan", izoh])
        
        keyboard = [["/yangi", "/tolandi"], ["/royxat", "/hisobot"]]
        await update.message.reply_text(
            f"Saqlandi!\n\n"
            f"Mijoz: {mijoz}\n"
            f"Buyurtma: {buyurtma}\n"
            f"Summa: {summa:,} so'm\n"
            f"Sana: {sana}\n"
            f"Holat: To'lanmagan",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
    except Exception as e:
        await update.message.reply_text(f"Xatolik: {e}")
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["/yangi", "/tolandi"], ["/royxat", "/hisobot"]]
    await update.message.reply_text(
        "Bekor qilindi.",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return ConversationHandler.END

async def tolandi_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sheet = get_sheet()
        records = sheet.get_all_records()
        
        tolanmaganlar = [
            (i+2, r) for i, r in enumerate(records)
            if r.get("Holat", "") == "To'lanmagan"
        ]
        
        if not tolanmaganlar:
            await update.message.reply_text("Barcha qarzlar to'langan!")
            return ConversationHandler.END
        
        context.user_data["tolanmaganlar"] = tolanmaganlar
        
        keyboard = []
        for row_num, r in tolanmaganlar:
            keyboard.append([f"{r['Mijoz']} — {r['Summa']:,} so'm"])
        keyboard.append(["Bekor qilish"])
        
        await update.message.reply_text(
            "Qaysi mijoz to'ladi?",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return TOLANDI_MIJOZ
    except Exception as e:
        await update.message.reply_text(f"Xatolik: {e}")
        return ConversationHandler.END

async def tolandi_mijoz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Bekor qilish":
        return await cancel(update, context)
    
    tanlangan = update.message.text
    tolanmaganlar = context.user_data.get("tolanmaganlar", [])
    
    try:
        sheet = get_sheet()
        for row_num, r in tolanmaganlar:
            label = f"{r['Mijoz']} — {r['Summa']:,} so'm"
            if label == tanlangan:
                sheet.update_cell(row_num, 5, "To'langan")
                keyboard = [["/yangi", "/tolandi"], ["/royxat", "/hisobot"]]
                await update.message.reply_text(
                    f"{r['Mijoz']} — {r['Summa']:,} so'm to'langan deb belgilandi!",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
                return ConversationHandler.END
        
        await update.message.reply_text("Topilmadi, qaytadan tanlang.")
        return TOLANDI_MIJOZ
    except Exception as e:
        await update.message.reply_text(f"Xatolik: {e}")
        return ConversationHandler.END

async def royxat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sheet = get_sheet()
        records = sheet.get_all_records()
        
        if not records:
            await update.message.reply_text("Hozircha qarz yo'q.")
            return
        
        tolanmaganlar = [r for r in records if r.get("Holat") == "To'lanmagan"]
        
        if not tolanmaganlar:
            await update.message.reply_text("Barcha qarzlar to'langan!")
            return
        
        jami = sum(r.get("Summa", 0) for r in tolanmaganlar)
        
        matn = "To'lanmagan qarzlar:\n\n"
        for r in tolanmaganlar:
            matn += f"👤 {r['Mijoz']}\n"
            matn += f"   {r['Buyurtma']} — {r['Summa']:,} so'm\n"
            matn += f"   {r['Sana']}\n\n"
        
        matn += f"Jami: {jami:,} so'm"
        await update.message.reply_text(matn)
    except Exception as e:
        await update.message.reply_text(f"Xatolik: {e}")

async def hisobot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sheet = get_sheet()
        records = sheet.get_all_records()
        
        hafta_oldin = datetime.now() - timedelta(days=7)
        
        bu_hafta = []
        for r in records:
            try:
                sana = datetime.strptime(r["Sana"], "%d.%m.%Y")
                if sana >= hafta_oldin:
                    bu_hafta.append(r)
            except:
                pass
        
        jami_qarz = sum(r.get("Summa", 0) for r in records if r.get("Holat") == "To'lanmagan")
        bu_hafta_tolangan = sum(r.get("Summa", 0) for r in bu_hafta if r.get("Holat") == "To'langan")
        bu_hafta_yangi = sum(r.get("Summa", 0) for r in bu_hafta if r.get("Holat") == "To'lanmagan")
        
        matn = (
            f"Haftalik hisobot ({datetime.now().strftime('%d.%m.%Y')})\n\n"
            f"Bu hafta kiritilgan: {bu_hafta_yangi:,} so'm\n"
            f"Bu hafta to'langan: {bu_hafta_tolangan:,} so'm\n"
            f"Umumiy qoldiq qarz: {jami_qarz:,} so'm"
        )
        await update.message.reply_text(matn)
    except Exception as e:
        await update.message.reply_text(f"Xatolik: {e}")

async def haftalik_hisobot_avtomatik(context: ContextTypes.DEFAULT_TYPE):
    try:
        sheet = get_sheet()
        records = sheet.get_all_records()
        
        hafta_oldin = datetime.now() - timedelta(days=7)
        bu_hafta = []
        for r in records:
            try:
                sana = datetime.strptime(r["Sana"], "%d.%m.%Y")
                if sana >= hafta_oldin:
                    bu_hafta.append(r)
            except:
                pass
        
        jami_qarz = sum(r.get("Summa", 0) for r in records if r.get("Holat") == "To'lanmagan")
        bu_hafta_tolangan = sum(r.get("Summa", 0) for r in bu_hafta if r.get("Holat") == "To'langan")
        bu_hafta_yangi = sum(r.get("Summa", 0) for r in bu_hafta if r.get("Holat") == "To'lanmagan")
        
        matn = (
            f"Avtomatik haftalik hisobot ({datetime.now().strftime('%d.%m.%Y')})\n\n"
            f"Bu hafta kiritilgan: {bu_hafta_yangi:,} so'm\n"
            f"Bu hafta to'langan: {bu_hafta_tolangan:,} so'm\n"
            f"Umumiy qoldiq qarz: {jami_qarz:,} so'm"
        )
        await context.bot.send_message(chat_id=DIRECTOR_CHAT_ID, text=matn)
    except Exception as e:
        logger.error(f"Hisobot xatolik: {e}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    yangi_conv = ConversationHandler(
        entry_points=[CommandHandler("yangi", yangi_start)],
        states={
            MIJOZ: [MessageHandler(filters.TEXT & ~filters.COMMAND, yangi_mijoz)],
            BUYURTMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, yangi_buyurtma)],
            SUMMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, yangi_summa)],
            IZOH: [MessageHandler(filters.TEXT & ~filters.COMMAND, yangi_izoh)],
        },
        fallbacks=[CommandHandler("bekor", cancel)]
    )
    
    tolandi_conv = ConversationHandler(
        entry_points=[CommandHandler("tolandi", tolandi_start)],
        states={
            TOLANDI_MIJOZ: [MessageHandler(filters.TEXT & ~filters.COMMAND, tolandi_mijoz)],
        },
        fallbacks=[CommandHandler("bekor", cancel)]
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(yangi_conv)
    app.add_handler(tolandi_conv)
    app.add_handler(CommandHandler("royxat", royxat))
    app.add_handler(CommandHandler("hisobot", hisobot))
    
    job_queue = app.job_queue
    job_queue.run_repeating(
        haftalik_hisobot_avtomatik,
        interval=timedelta(weeks=1),
        first=timedelta(seconds=10)
    )
    
    logger.info("Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
