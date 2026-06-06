import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ========== НАСТРОЙКИ (УЖЕ ЗАПОЛНЕНЫ) ==========
TOKEN = "8891824297:AAEUUcKwsDc8H5JR_W8WAdleyNgOIqSU-20"
CHAT_ID = 468617242  # ТВОЙ CHAT_ID
DATA_FILE = "birthdays.json"

# ========== РАБОТА С ФАЙЛОМ ==========
def load_birthdays():
    if not Path(DATA_FILE).exists():
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_birthdays(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
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

def days_until_birthday(day, month):
    today = datetime.now().date()
    birthday_this_year = datetime(today.year, month, day).date()
    if birthday_this_year >= today:
        return (birthday_this_year - today).days
    else:
        birthday_next_year = datetime(today.year + 1, month, day).date()
        return (birthday_next_year - today).days

# ========== КОМАНДЫ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎂 Привет! Я напоминаю о днях рождения сотрудников.\n\n"
        "📌 Команды:\n"
        "/add Имя Фамилия ДД.ММ.ГГГГ — добавить\n"
        "/list — список всех ДР\n"
        "/remove Имя Фамилия — удалить\n"
        "/help — помощь"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def add_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Пример: /add Иван Петров 15.08.1990")
        return
    try:
        date_str = context.args[-1]
        name = " ".join(context.args[:-1])
        if not name:
            raise ValueError("Укажите имя")
        day, month, year = parse_date(date_str)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        return

    data = load_birthdays()
    if name in data:
        await update.message.reply_text(f"⚠️ {name} уже есть. Удалите сначала /remove")
        return

    data[name] = {
        "day": day,
        "month": month,
        "year": year,
        "full_date": f"{day:02d}.{month:02d}" + (f".{year}" if year else "")
    }
    save_birthdays(data)
    await update.message.reply_text(f"✅ Добавлен: {name} ({data[name]['full_date']})")

async def list_birthdays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_birthdays()
    if not data:
        await update.message.reply_text("📭 Список пуст.")
        return

    msg = "🎈 *Список дней рождения:*\n\n"
    for name, info in data.items():
        msg += f"• {name} — {info['full_date']}\n"
    
    upcoming = []
    for name, info in data.items():
        days_left = days_until_birthday(info["day"], info["month"])
        if days_left <= 14:
            upcoming.append((days_left, name))
    upcoming.sort(key=lambda x: x[0])
    
    if upcoming:
        msg += "\n🟢 *Ближайшие (до 14 дней):*\n"
        for days, name in upcoming:
            msg += f"  {name} — через {days} дн.\n"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def remove_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Пример: /remove Иван Петров")
        return
    name = " ".join(context.args)
    data = load_birthdays()
    if name not in data:
        await update.message.reply_text(f"❌ {name} не найден")
        return
    del data[name]
    save_birthdays(data)
    await update.message.reply_text(f"🗑 Удалён: {name}")

# ========== ЕЖЕДНЕВНАЯ РАССЫЛКА ==========
async def send_birthday_reminders(context: ContextTypes.DEFAULT_TYPE):
    data = load_birthdays()
    if not data:
        return
    
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    
    messages = []
    for name, info in data.items():
        b_day = info["day"]
        b_month = info["month"]
        
        if today.day == b_day and today.month == b_month:
            age = ""
            if info["year"]:
                age = today.year - info["year"]
                age = f" (исполняется {age})"
            messages.append(f"🎉 СЕГОДНЯ ДР у {name}{age}! Поздравляем! 🎂")
        elif tomorrow.day == b_day and tomorrow.month == b_month:
            messages.append(f"🔔 ЗАВТРА день рождения у {name}. Не забудьте поздравить!")
    
    if messages:
        await context.bot.send_message(chat_id=CHAT_ID, text="\n\n".join(messages))

# ========== ЗАПУСК ==========
async def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add", add_birthday))
    app.add_handler(CommandHandler("list", list_birthdays))
    app.add_handler(CommandHandler("remove", remove_birthday))
    
    # Ежедневно в 09:00
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_daily(send_birthday_reminders, time=datetime.strptime("09:00", "%H:%M").time())
    
    print("🤖 Бот запущен! Напиши /start в Telegram")
    print(f"📨 Уведомления будут приходить в чат с ID: {CHAT_ID}")
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())