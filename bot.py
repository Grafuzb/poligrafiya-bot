import logging
import os
import json
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

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "")
DIRECTOR_CHAT_ID = os.environ.get("DIRECTOR_CHAT_ID", "")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_sheet():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS", "")
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    return sheet

MIJOZ, BUYURTMA, SUMMA, IZOH = range(4)
TOLANDI_MIJOZ = range(4, 5)

def main_keyboard():
    return ReplyKeyboardMarkup([["/yangi", "/tolandi"], ["/royxat", "/hisobot"]], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! Poligrafiya qarz boti.\n\n/yangi - yangi qarz\n/tolandi - tolov belgilash\n/royxat - qarzlar royxati\n/hisobot - haftalik hisobot",
        reply_markup=main_keyboard()
    )

async def yangi_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Mijoz ismini kiriting:", reply_markup=ReplyKeyboardRemove())
    return MIJOZ

async def yangi_mijoz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mijoz"] = update.message.text
    keyboard = [["Vizitka", "Banner"], ["Kitob", "Buklet"], ["Boshqa"]]
    await update.message.reply_text("Buyurtma turini tanlang:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return BUYURTMA

async def yangi_buyurtma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["buyurtma"] = update.message.text
    await update.message.reply_text("Qarz summasini kiriting (som):", reply_markup=ReplyKeyboardRemove())
    return SUMMA

async def yangi_summa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        summa = int(update.message.text.replace(" ", "").replace(",", ""))
        context.user_data["summa"] = summa
    except ValueError:
        await update.message.reply_text("Faqat raqam kiriting:")
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
        sheet.append_row([mijoz, buyurtma, summa, sana, "Tolanmagan", izoh])
        await update.message.reply_text(
            f"Saqlandi!\n\nMijoz: {mijoz}\nBuyurtma: {buyurtma}\nSumma: {summa:,} som\nSana: {sana}\nHolat: Tolanmagan",
            reply_markup=main_keyboard()
        )
    except Exception as e:
        await update.message.reply_text(f"Xatolik: {e}")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bekor qilindi.", reply_markup=main_keyboard())
    return ConversationHandler.END

async def tolandi_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sheet = get_sheet()
        records = sheet.get_all_records()
        tolanmaganlar = [(i+2, r) for i, r in enumerate(records) if r.get("Holat", "") == "Tolanmagan"]
        if not tolanmaganlar:
            await update.message.reply_text("Barcha qarzlar tolangan!", reply_markup=main_keyboard())
            return ConversationHandler.END
        context.user_data["tolanmaganlar"] = tolanmaganlar
        keyboard = [[f"{r['Mijoz']} - {r['Summa']:,} som"] for _, r in tolanmaganlar]
        keyboard.append(["Bekor qilish"])
        await update.message.reply_text("Qaysi mijoz toladi?", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
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
            label = f"{r['Mijoz']} - {r['Summa']:,} som"
            if label == tanlangan:
                sheet.update_cell(row_num, 5, "Tolangan")
                await update.message.reply_text(f"{r['Mijoz']} tolangan deb belgilandi!", reply_markup=main_keyboard())
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
        tolanmaganlar = [r for r in records if r.get("Holat") == "Tolanmagan"]
        if not tolanmaganlar:
            await update.message.reply_text("Barcha qarzlar tolangan!")
            return
        jami = sum(r.get("Summa", 0) for r in tolanmaganlar)
        matn = "Tolanmagan qarzlar:\n\n"
        for r in tolanmaganlar:
            matn += f"Mijoz: {r['Mijoz']}\n{r['Buyurtma']} - {r['Summa']:,} som\nSana: {r['Sana']}\n\n"
        matn += f"Jami: {jami:,} som"
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
        jami_qarz = sum(r.get("Summa", 0) for r in records if r.get("Holat") == "Tolanmagan")
        bu_hafta_tolangan = sum(r.get("Summa", 0) for r in bu_hafta if r.get("Holat") == "Tolangan")
        bu_hafta_yangi = sum(r.get("Summa", 0) for r in bu_hafta if r.get("Holat") == "Tolanmagan")
        matn = (
            f"Haftalik hisobot ({datetime.now().strftime('%d.%m.%Y')})\n\n"
            f"Bu hafta kiritilgan: {bu_hafta_yangi:,} som\n"
            f"Bu hafta tolangan: {bu_hafta_tolangan:,} som\n"
            f"Umumiy qoldiq: {jami_qarz:,} som"
        )
        await update.message.reply_text(matn)
    except Exception as e:
        await update.message.reply_text(f"Xatolik: {e}")

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

    logger.info("Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
