from telegram_messenger import AlertHandler, TelegramBot

# Still does not work correctly. Does not send the message to the bot.

# TODO: Move to VENV
TOKEN = "7949633686:AAHe8DWw9vpdkGPbDOyJfGZ82bXhe1PCChI"
# Initialize the bot
telegram_bot = TelegramBot(TOKEN)

sender = AlertHandler(telegram_bot)
sender.receive_alert("This is an alert message!")