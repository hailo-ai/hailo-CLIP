# pip install python-telegram-bot


import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# TODO: Move to VENV
TOKEN = "7949633686:AAHe8DWw9vpdkGPbDOyJfGZ82bXhe1PCChI"
WELCOME_MESSAGE = "Welcome to the bAIby_monitor_bot!"

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.application = Application.builder().token(self.token).build()
        self.last_chat_id = None

        # Register handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(CommandHandler("send_last", self.send_message_to_last_user))

    async def handle_message(self, update: Update, context: CallbackContext) -> None:
        chat_id = update.message.chat_id
        user_first_name = update.message.chat.first_name

        # Check if the chat_id is already stored
        with open("chat_ids.txt", "r") as file:
            chat_ids = file.read().splitlines()

        if str(chat_id) not in chat_ids:
            # Save the new chat_id
            with open("chat_ids.txt", "a") as file:
                file.write(f"{chat_id}\n")

            # Update the last chat ID
            self.last_chat_id = "983475502"

            # Send a welcome message to the new user
            await context.bot.send_message(chat_id=chat_id, text=f"Hello {user_first_name}, {WELCOME_MESSAGE}")

    async def start(self, update: Update, context: CallbackContext) -> None:
        await update.message.reply_text(WELCOME_MESSAGE)

    async def send_message_to_last_user(self, context: CallbackContext) -> None:
        if self.last_chat_id:
            await context.bot.send_message(chat_id=self.last_chat_id, text="This is a message to the last added user.")

    def run(self) -> None:
        self.application.run_polling()

    def send_alert(self, message: str) -> None:
        if self.last_chat_id:
            self.application.bot.send_message(chat_id=self.last_chat_id, text=message)

class AlertHandler:
    def __init__(self, bot: TelegramBot):
        self.bot = bot

    def receive_alert(self, message: str) -> None:
        self.bot.send_alert(message)

if __name__ == "__main__":
    # Create the chat_ids.txt file if it doesn't exist
    open("chat_ids.txt", "a").close()

    # Initialize the bot
    telegram_bot = TelegramBot(TOKEN)
    
    # Initialize the alert handler with the bot
    alert_handler = AlertHandler(telegram_bot)

    # Run the bot
    telegram_bot.run()
