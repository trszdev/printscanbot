from logging import basicConfig as configure_logging, INFO as logging_info
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler
from telegram.ext.filters import Filters
from tempfile import NamedTemporaryFile
from subprocess import check_output
from traceback import format_exc
from configparser import ConfigParser
from threading import Thread


is_scanning = False
queue = []


def whitelist(white_ids):
    def deco(handler):
        def wrapper(update, context):
            if update.effective_chat.id in white_ids:
                return handler(update, context)
        return wrapper
    return deco


def scan_async(message):
    t = Thread(target=scan, args=(message,), daemon=True)
    t.run()


def scan(message):
    global is_scanning
    try:
        is_scanning = True
        out = check_output('scanimage | pnmtopng > scan.png', timeout=600, shell=True)
        if out: raise OSError(out)
        with open('scan.png', 'rb') as image:
            message.reply_photo(image)
    except Exception:
        message.reply_markdown(f'При сканировании произошла ошибка: ```{format_exc()}```')
    finally:
        is_scanning = False


def cmd_start(update, context):
    keyboard = [[InlineKeyboardButton('Сканировать', callback_data='scan'),
                 InlineKeyboardButton('Печатать', callback_data='print')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Что мне делать?', reply_markup=reply_markup)


def button(update, context):
    query = update.callback_query
    global is_scanning
    if query.data == 'scan':
        if is_scanning:
            query.edit_message_text(text='Уже сканирую')
        else:
            query.edit_message_text(text='Хорошо, начинаю сканировать')
        scan_async(query.message)
    elif query.data == 'print':
        query.edit_message_text(text='Отправьте сюда файл для печати')


def cmd_print(update, context):
    update.message.reply_text('Отправьте сюда файл для печати')


def cmd_scan(update, context):
    global is_scanning
    if is_scanning:
        update.message.reply_text('Уже сканирую')
        return
    update.message.reply_text('Хорошо, начинаю сканировать')
    scan_async(update.message)


def cmd_message(update, context):
    msg = update.message
    file_id = msg.photo[-1].file_id if msg.photo else msg.document.file_id
    # document.mime_type, document.thumb
    queue.append(context.bot.get_file(file_id))
    with NamedTemporaryFile() as temp_file:
        context.bot.get_file(file_id).download(out=temp_file)
        update.message.reply_text(f'Saved attachment to {temp_file.name}')


def error(update, context):
    print('Update "%s" caused error "%s"', update, context.error)


def main(white_ids, token, proxy):
    updater = Updater(token, request_kwargs=proxy, use_context=True)
    w = whitelist(white_ids)
    updater.dispatcher.add_handler(CommandHandler('start', w(cmd_start)))
    updater.dispatcher.add_handler(CallbackQueryHandler(w(button)))
    updater.dispatcher.add_handler(CommandHandler('print', w(cmd_print)))
    updater.dispatcher.add_handler(CommandHandler('scan', w(cmd_scan)))
    updater.dispatcher.add_handler(MessageHandler(Filters.photo | Filters.document, w(cmd_message)))
    updater.dispatcher.add_error_handler(error)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    configure_logging(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging_info)
    c = ConfigParser()
    c.read('config.ini')
    if 'Bot' not in c:
        print("Bot section is missing in config.ini")
    elif 'token' not in c['Bot']:
        print("token isn't present in config.ini")
    elif 'white_ids' not in c['Bot']:
        print("white_ids isn't present in config.ini")
    else:
        ids = set(map(int, c['Bot']['white_ids'].split(',')))
        proxy = c['Bot'].get('proxy_url')
        main(ids, c['Bot']['token'], {'proxy_url': proxy} if proxy else {})
