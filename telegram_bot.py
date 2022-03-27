import os, logging, configparser
from pyzbar import pyzbar
from PIL import Image
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
import database.db_interactor as db_interactor
from database.db_tools import db_connect

#HERBIE TELEGRAM BOT
#Config:
config = configparser.ConfigParser()
print(os.getcwd())
config.read(os.getcwd()+"/t_credentials.ini")
t_conf = config['TELEGRAM']
TOKEN = str(t_conf.get('token'))

#Set Telegram logger:
tlog=logging.getLogger('tbot_interactions')
thdl=logging.FileHandler('./logs/tbot_interactions.log',mode='a')
thdl.setFormatter(logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s'))
tlog.setLevel(logging.INFO)
tlog.addHandler(thdl)

START, ASK_PCODE, ASK_SUPPLIER, ASK_PNAME, ASK_CATEGORY, ASK_QUANTITY, ASK_NEXT = range(7)

#START:
def start(update: Update, context: CallbackContext) -> int:
    """Starts the conversation and asks the user about their gender."""
    reply_keyboard = [['Boy', 'Girl', 'Other']]

    update.message.reply_text(
        "Hi! My name is Professor Bot. I will hold a conversation with you. "
        "Send /cancel to stop talking to me.\n\n"
        "Are you a boy or a girl?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Boy or Girl?'
        ),
    )

    return START


#ADD NEW PRODUCT TO DB:
#1) p_code: text or photo:
def nuovo(update: Update, context: CallbackContext) -> int:
    msg = "Ciao! Registriamo un nuovo prodotto al tuo magazzino.\n\nPer prima cosa, mi serve il <b>codice a barre</b>: puoi trascrivermelo via <i>testo</i>, oppure inviarmi una <i>foto</i>.\nCosa preferisci?"
    reply_keyboard = [['Trascrivo'], ['Invio foto']]
    update.message.reply_text(msg,
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, input_field_placeholder='Scegli qui:'))
    return ASK_PCODE

#2.a) store mode preference and ask for p_code photo:
def pcode_ask_photo(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    context.user_data['choice'] = text
    msg = "Scatta una <b>foto</b> al codice a barre del prodotto e inviamela qui.\nOppure scrivi /esci per uscire."
    update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardRemove())
    return ASK_SUPPLIER

#2.b) store mode preference and ask for p_code text:
def pcode_ask_text(update: Update, context: CallbackContext) -> int:
    msg = "Trascrivimi il <b>codice a barre</b> del prodotto. Solo numeri, senza spazi.\nOppure scrivi /esci per uscire."
    update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardRemove())
    return ASK_SUPPLIER

#3.a) process p_code from barcode photo:
def pcode_process_photo(update: Update, context: CallbackContext) -> int:
    #get photo sent by user:
    image_name = './telegram_bot/data_cache/barcode.jpg'
    image = update.message.photo[-1].get_file()
    image.download(image_name)
    #read barcode in photo:
    decoded = pyzbar.decode(Image.open(image_name))
    p_code = decoded[0].data
    p_code = p_code.decode("utf-8")
    #store barcode in bot memory:
    context.user_data['p_code'] = p_code
    tlog.info(f"Letto codice {p_code}, type {type(p_code)}.")
    #next message:
    msg = f"Ho letto il codice {p_code}! Ora scrivimi il nome del <b>produttore</b>.\nOppure scrivi /esci per uscire."
    update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    return ASK_PNAME

#3.b) process p_code from text:
def pcode_process_text(update: Update, context: CallbackContext) -> int:
    #get code sent by user:
    p_code = update.message.text
    #store barcode in bot memory:
    context.user_data['p_code'] = p_code
    tlog.info(f"Letto codice {p_code}, type {type(p_code)}.")
    #next message:
    msg = f"Ho letto il codice {p_code}! Ora scrivimi il nome del <b>produttore</b>.\nOppure scrivi /esci per uscire."
    update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    return ASK_PNAME

#4) process supplier and ask p_name:
def supplier_to_pname(update: Update, context: CallbackContext) -> int:
    #get supplier name sent by user:
    supplier = update.message.text.lower()
    #store in bot memory:
    context.user_data['supplier'] = supplier
    tlog.info(f"Letto produttore {supplier}.")
    #next message:
    msg = f"Salvato produttore {supplier}! Ora scrivimi il nome dettagliato del <b>prodotto</b>. Aggiungi tutte le info necessarie, es.:\n\n<i>Grintuss pediatric sciroppo 12 flaconcini</i>\n\nOppure scrivi /esci per uscire."
    update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    return ASK_CATEGORY

#5) process p_name and ask_category:
def pname_to_category(update: Update, context: CallbackContext) -> int:
    #get prod name sent by user:
    p_name = update.message.text.lower()
    #store in bot memory:
    context.user_data['p_name'] = p_name
    tlog.info(f"Letto nome prodotto {p_name}.")
    #next message:
    msg = f"Salvato nome {p_name}! Ora dimmi a quale <b>categoria</b> appartiene (es. cosmesi, alimentazione, ...). Usa <b>UNA sola parola</b>.\nOppure scrivi /esci per uscire."
    update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    return ASK_QUANTITY

#6) process category and ask_quantity:
def category_to_quantity(update: Update, context: CallbackContext) -> int:
    #get prod name sent by user:
    cat = update.message.text.lower()
    #store in bot memory:
    context.user_data['category'] = cat
    tlog.info(f"Letta categoria {cat}.")
    #next message:
    msg = f"Salvata categoria {cat}! Mi dici il <b>numero di pezzi</b> che hai in magazzino?\nScrivi solo in <i>cifre</i>, es. 1, 10, ...\nOppure scrivi /esci per uscire."
    update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    return ASK_NEXT

#6) process category and ask_quantity:
def save_to_db(update: Update, context: CallbackContext) -> int:
    #get prod name sent by user:
    pieces = update.message.text.lower()
    #store in bot memory:
    context.user_data['pieces'] = pieces
    tlog.info(f"Letti {pieces} pezzi.")
    #store all in DB:
    utts = {
        'p_code': int(context.user_data['p_code']),
        'supplier': context.user_data['supplier'],
        'p_name': context.user_data['p_name'],
        'category': context.user_data['category'],
        'pieces': int(context.user_data['pieces']),
    }
    try:
        conn, cursor = db_connect()
        ret = db_interactor.add_prod(conn, cursor, utts)
        conn.close()
        msg = f"Ti ho salvato il prodotto nel magazzino! Vuoi che ti faccia qualche altra domanda per categorizzare meglio il prodotto?"
        reply_keyboard = [['Sì'], ['No']]
        update.message.reply_text(msg,
            parse_mode=ParseMode.HTML,
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, input_field_placeholder='Scegli:'))
    except:
        msg = f"C'è stato un problema col mio DB, ti chiedo scusa!"
        update.message.reply_text(msg)
    return ConversationHandler.END


#CANCEL AND END:
def esci(update: Update, context: CallbackContext) -> int:
    msg = "Uscito. A presto!"
    update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


#MAIN:
def main() -> None:
    #create the Updater and pass it the bot's token:
    updater = Updater(TOKEN)
    #get the dispatcher to register handlers:
    dispatcher = updater.dispatcher

    #conv handler: add new product ("/nuovo"):
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('nuovo', nuovo)],
        states={
            ASK_PCODE: [
                MessageHandler(Filters.regex('^Trascrivo$'), pcode_ask_text),
                MessageHandler(Filters.regex('^Invio foto$'), pcode_ask_photo)],
            ASK_SUPPLIER: [
                MessageHandler(Filters.photo, pcode_process_photo),
                MessageHandler(Filters.text, pcode_process_text)],
            ASK_PNAME: [
                MessageHandler(Filters.text, supplier_to_pname)],
            ASK_CATEGORY: [
                MessageHandler(Filters.text, pname_to_category)],
            ASK_QUANTITY: [
                MessageHandler(Filters.text, category_to_quantity)],
            ASK_NEXT: [
                MessageHandler(Filters.text, save_to_db)],
        },
        fallbacks=[CommandHandler('esci', esci)])
    dispatcher.add_handler(conv_handler)

    #start polling:
    updater.start_polling()

    #idle:
    updater.idle()


if __name__ == '__main__':
    main()
