import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID", 468617242))
DATA_FILE = "birthdays.json"

if not TOKEN:
    print("❌ Ошибка: BOT_TOKEN не задан")
    exit(1)

def load_birthdays():
    if not Path(DATA_FILE).exists():
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_birthdays(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def parse_date(date_str):
    parts = date_str.strip().split('.')
    if len(parts) == 2:
        day, month = int(parts[0]), int(parts[1])
        return (day, month, None)
    elif len(parts) == 3:
        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
        return (day, month, year)
    else:
        raise ValueError("Нужно ДД.ММ или ДД.ММ.ГГГГ")

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🎂 Привет! Я напоминаю о днях рождения.\n\n"
        "/add Имя ДД.ММ — добавить\n"
        "/list — список всех ДР\n"
        "/remove Имя — удалить"
    )

def add_birthday(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("❌ Пример: /add Анна 15.08")
        return
    try:
        date_str = context.args[-1]
        name = " ".join(context.args[:-1])
        day, month, year = parse_date(date_str)
    except Exception as e:
        update.message.reply_text(f"❌ Ошибка: {e}")
        return

    data = load_birthdays()
    if name in data:
        update.message.reply_text(f"⚠️ {name} уже есть")
        return

    data[name] = {
        "day": day,
        "month": month,
        "year": year,
        "full_date": f"{day:02d}.{month:02d}"
    }
    save_birthdays(data)
    update.message.reply_text(f"✅ Добавлен: {name} ({data[name]['full_date']})")

def list_birthdays(update: Update, context: CallbackContext):
    data = load_birthdays()
    if not data:
        update.message.reply_text("📭 Список пуст.")
        return

    msg = "🎈 *Список ДР:*\n\n"
    for name, info in data.items():
        msg += f"• {name} — {info['full_date']}\n"
    
    update.message.reply_text(msg, parse_mode="Markdown")

def remove_birthday(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("❌ Пример: /remove Анна")
        return
    name = " ".join(context.args)
    data = load_birthdays()
    if name not in data:
        update.message.reply_text(f"❌ {name} не найден")
        return
    del data[name]
    save_birthdays(data)
    update.message.reply_text(f"🗑 Удалён: {name}")

def send_monthly_reminder(context: CallbackContext):
    data = load_birthdays()
    if not data:
        return
    
    today = datetime.now()
    current_month = today.month
    today_day = today.day
    
    if not ((1 <= today_day <= 5) or (20 <= today_day <= 25)):
        return
    
    birthdays_this_month = []
    for name, info in data.items():
        if info["month"] == current_month:
            birthdays_this_month.append((info["day"], name))
    
    if not birthdays_this_month:
        return
    
    birthdays_this_month.sort(key=lambda x: x[0])
    
    month_name = {
        1: "Январе", 2: "Феврале", 3: "Марте", 4: "Апреле",
        5: "Мае", 6: "Июне", 7: "Июле", 8: "Августе",
        9: "Сентябре", 10: "Октябре", 11: "Ноябре", 12: "Декабре"
    }[current_month]
    
    message = f"📅 *НАПОМИНАНИЕ О ДНЯХ РОЖДЕНИЯ*\n\n"
    message += f"В {month_name} день рождения у:\n\n"
    
    for day, name in birthdays_this_month:
        message += f"• *{name}*\n  🎂 {day:02d}.{current_month:02d}\n\n"
    
    message += "Не забудь собрать дань! ლ(ಠ_ಠ ლ)"
    
    context.bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("add", add_birthday))
    dp.add_handler(CommandHandler("list", list_birthdays))
    dp.add_handler(CommandHandler("remove", remove_birthday))
    
    jq = updater.job_queue
    jq.run_daily(send_monthly_reminder, time=datetime.strptime("10:00", "%H:%M").time())
    
    print("🤖 Бот запущен!")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
