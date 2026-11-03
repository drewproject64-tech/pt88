"""PT88 text utilities. Configure BOT_TOKEN in the hosting environment."""
import asyncio
import logging
import os
import re
from io import BytesIO
from telegram import BotCommand, ReplyKeyboardMarkup, Update
from telegram.error import NetworkError, RetryAfter, TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

NAME = 'PT88B88_Bot'
USERNAME = 'PT88_B88_Bot'
ABOUT = 'Clean text, count words and characters, and convert letter case directly in Telegram.'
DESCRIPTION = ('PT88B88_Bot provides three simple text tools: Clean Text removes extra spaces and blank lines; '
               'Word Counter counts words, characters and lines; Case Converter returns uppercase and lowercase versions. '
               'Send text to clean it immediately, or choose one of the three tools. Results appear in this chat. '
               'No account or payment required. Use /privacy for data information.')
BUTTONS = ('Clean Text', 'Word Counter', 'Case Converter')
KEYBOARD = ReplyKeyboardMarkup([[b] for b in BUTTONS], resize_keyboard=True, is_persistent=True)
LOG = logging.getLogger(__name__)


def clean_text(text):
    return '\n'.join(re.sub(r'[^\S\n]+', ' ', line).strip() for line in text.splitlines() if line.strip())


def word_count(text):
    words = len(re.findall(r"\w+(?:['’\-]\w+)*", text, re.UNICODE))
    return (f'Words: {words}\nCharacters (including spaces): {len(text)}\n'
            f'Characters (excluding whitespace): {sum(not c.isspace() for c in text)}\nLines: {len(text.splitlines())}')


def convert_case(text):
    return f'UPPERCASE\n{text.upper()}\n\nlowercase\n{text.lower()}'


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.effective_message.reply_text(
        f'{NAME} — three text tools in this chat.\n\n'
        'Clean Text: remove extra spaces and blank lines.\n'
        'Word Counter: count words, characters and lines.\n'
        'Case Converter: get uppercase and lowercase copies.\n\n'
        'Tap a tool, then send text. Or send text now to clean it immediately.\n'
        'Example: send "Hello   world" to receive "Hello world".\n'
        'Use /help for instructions or /privacy for data information.', reply_markup=KEYBOARD)


async def help_command(update, context):
    await update.effective_message.reply_text(
        'Clean Text: removes repeated spaces and empty lines, keeping nonempty line breaks.\n'
        'Word Counter: counts words, characters and lines. Words use letters/numbers separated by punctuation or spaces.\n'
        'Case Converter: provides uppercase and lowercase copies.\n'
        'Choose a button, then send a text message (up to 4,000 characters). '
        'The selected tool stays active. /start or /cancel resets your selection.', reply_markup=KEYBOARD)


async def privacy(update, context):
    await update.effective_message.reply_text(
        'Your text is processed in memory to generate a reply. This application does not save message text '
        'to a database or log it, and does not forward it to third-party AI services. '
        'Only your selected tool is kept in memory until reset or restart. '
        'Messages remain in your Telegram chat under Telegram’s own data policies. Avoid sending sensitive information.',
        reply_markup=KEYBOARD)


async def respond(update, context):
    message = update.effective_message
    text = message.text
    if text in BUTTONS:
        context.user_data['tool'] = text
        examples = {
            BUTTONS[0]: 'Example: "Hello   world" becomes "Hello world".',
            BUTTONS[1]: 'Example: "Hello world" contains 2 words and 11 characters.',
            BUTTONS[2]: 'Example: "Hello" becomes "HELLO" and "hello".',
        }
        await message.reply_text(f'{text} selected. Send your text now.\n{examples[text]}', reply_markup=KEYBOARD)
        return
    tool = context.user_data.setdefault('tool', BUTTONS[0])
    if not text.strip():
        await message.reply_text('Please send text containing at least one visible character.', reply_markup=KEYBOARD)
        return
    if len(text) > 4000:
        await message.reply_text('Please send up to 4,000 characters at a time.', reply_markup=KEYBOARD)
        return
    result = {BUTTONS[0]: clean_text, BUTTONS[1]: word_count, BUTTONS[2]: convert_case}[tool](text)
    # UTF-16 length protects Telegram's limit for emoji and expanded case conversions.
    if len(result.encode('utf-16-le')) // 2 > 3900:
        output = BytesIO(result.encode('utf-8'))
        output.name = 'pt88-result.txt'
        await message.reply_document(output, caption='Your text result.', reply_markup=KEYBOARD)
    else:
        await message.reply_text(result, reply_markup=KEYBOARD)


async def unsupported(update, context):
    await update.effective_message.reply_text('Please send a text message. Use /help for instructions.', reply_markup=KEYBOARD)


async def setup(application):
    if application.bot.username.lower() != USERNAME.lower():
        raise RuntimeError('BOT_TOKEN belongs to a different bot; configure the token for @' + USERNAME)
    operations = [
        lambda: application.bot.set_my_name(NAME),
        lambda: application.bot.set_my_short_description(ABOUT),
        lambda: application.bot.set_my_description(DESCRIPTION),
        lambda: application.bot.set_my_commands([BotCommand('start', 'Open the three tools'),
                 BotCommand('help', 'How to use the tools'), BotCommand('cancel', 'Reset tool selection'),
                 BotCommand('privacy', 'How your text is handled')]),
    ]
    for operation in operations:
        for attempt in range(3):
            try:
                await operation()
                break
            except (NetworkError, RetryAfter) as exc:
                delay = getattr(exc, 'retry_after', 2 ** attempt)
                if hasattr(delay, 'total_seconds'):
                    delay = delay.total_seconds()
                if attempt == 2:
                    LOG.warning('Profile setup incomplete; retrying in five minutes.')
                    application.create_task(retry_setup(application))
                    return
                await asyncio.sleep(float(delay) + 1)
            except TelegramError:
                LOG.warning('A profile setting was rejected; check profile manually in BotFather.')
                break


async def retry_setup(application):
    await asyncio.sleep(300)
    if application.running:
        await setup(application)


async def on_error(update, context):
    # Never log raw exceptions: HTTP error strings can contain the bot token.
    LOG.warning('Update failed (%s).', type(context.error).__name__)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text('Unable to complete that request. Please try again or use /start.', reply_markup=KEYBOARD)
        except TelegramError:
            pass


def build_application(token):
    app = (Application.builder().token(token).post_init(setup)
           .connect_timeout(30).read_timeout(30).write_timeout(30)
           .get_updates_connect_timeout(30).get_updates_read_timeout(40).build())
    private = filters.ChatType.PRIVATE
    for command, handler in [('start', start), ('cancel', start), ('help', help_command), ('privacy', privacy)]:
        app.add_handler(CommandHandler(command, handler, filters=private))
    app.add_handler(MessageHandler(private & filters.TEXT & ~filters.COMMAND, respond))
    app.add_handler(MessageHandler(private, unsupported))
    app.add_error_handler(on_error)
    return app


if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.CRITICAL)
    token = os.environ.get('BOT_TOKEN', '').strip()
    if not token:
        raise SystemExit('Set BOT_TOKEN in the hosting environment before starting.')
    build_application(token).run_polling(allowed_updates=['message'], timeout=25, bootstrap_retries=5)
