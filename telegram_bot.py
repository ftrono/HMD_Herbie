from telegram import ReplyKeyboardRemove, Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler, CallbackContext
import database.db_interactor as db_interactor
from database.db_tools import db_connect
import telegram_support.bot_functions as bot_functions
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from globals import *

#HERBIE TELEGRAM BOT
#GLOBALS:
START, ASK_PCODE, PROCESS_PCODE, PROCESS_SUPPLIER, PROCESS_PNAME, PROCESS_CATEGORY, PROCESS_PIECES, SAVE, ASK_REWRITE = range(9)
CONV_END = -1 #value of ConversationHandler.END

#START:
def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Ciao!")
    return START

def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')

def echo(update, context):
    """Echo the user message."""
    update.message.reply_text(update.message.text)

#ADD NEW PRODUCT TO DB:
#1) p_code: text or photo:
def nuovo(update: Update, context: CallbackContext) -> int:
    msg = "Ciao! Registriamo un nuovo prodotto al tuo magazzino.\n\nPer prima cosa, mi serve il <b>codice a barre</b>: puoi trascrivermelo via <i>testo</i>, oppure inviarmi una <i>foto</i>.\nCosa preferisci?\n\nOppure scrivi /esci per uscire."
    keyboard = [[InlineKeyboardButton('Trascrivo', callback_data='Trascrivo'),
                InlineKeyboardButton('Invio foto', callback_data='Invio foto')]]
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard))
    return ASK_PCODE

#2) ask for p_code (photo or text):
def ask_pcode(update: Update, context: CallbackContext) -> int:
    #get open query:
    query = update.callback_query
    choice = query.data
    tlog.info(choice)
    #answer query:
    query.edit_message_reply_markup(reply_markup=None)
    query.answer()
    #next message:
    if choice == 'Invio foto':
        msg = "Inviami una <b>FOTO</b> del codice a barre del prodotto.\n\nOppure scrivi /esci per uscire."
    else:
        msg = "Trascrivimi il <b>codice a barre</b> del prodotto.\n\nSolo numeri, senza spazi.\n\nOppure scrivi /esci per uscire."
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg, 
        parse_mode=ParseMode.HTML, 
        reply_markup=None)
    return PROCESS_PCODE

#3.a) process p_code from barcode photo:
def pcode_process_photo(update: Update, context: CallbackContext) -> int:
    msg = f"Sto estraendo i dati..."
    message = context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
    try:
        #extract and store barcode from image:
        image = update.message.photo[-1].get_file()
        p_code = bot_functions.extract_barcode(image)
        context.user_data['p_code'] = p_code
        tlog.info(f"Letto codice {p_code}, type {type(p_code)}.")
        msg = f"Ho letto il codice {p_code}! Ora dimmi il nome del <b>produttore</b>.\n\nOppure scrivi /esci per uscire."
    except:
        msg = f"Non ho trovato codici.\n\nProva con un'altra foto, o in alternativa trascrivimi il codice a barre.\n\nOppure scrivi /esci per uscire."
        message.edit_text(text=msg)
        return PROCESS_PCODE
    #supplier picker:
    keyboard = bot_functions.inline_picker('Produttore')
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard != [] else None
    message.edit_text(text=msg,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup)
    return PROCESS_SUPPLIER

#3.b) process p_code from text:
def pcode_process_text(update: Update, context: CallbackContext) -> int:
    #get code sent by user:
    p_code = update.message.text
    #store barcode in bot memory:
    context.user_data['p_code'] = p_code
    tlog.info(f"Letto codice {p_code}, type {type(p_code)}.")
    msg = f"Ho letto il codice {p_code}! Ora dimmi il nome del <b>produttore</b>.\n\nOppure scrivi /esci per uscire."
    #supplier picker:
    keyboard = bot_functions.inline_picker('Produttore')
    update.message.reply_text(msg, 
        parse_mode=ParseMode.HTML, 
        reply_markup=InlineKeyboardMarkup(keyboard))
    return PROCESS_SUPPLIER

#4.a) new supplier:
def new_supplier(update: Update, context: CallbackContext) -> int:
    #get open query:
    query = update.callback_query
    choice = query.data
    #store choice:
    context.user_data['supplier'] = 'NEW'
    tlog.info(choice)
    #answer query:
    query.delete_message()
    query.answer()
    #ask new:
    msg = f"Scrivimi il nome del <b>produttore</b>.\n\nOppure scrivi /esci per uscire."
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode=ParseMode.HTML)
    return PROCESS_SUPPLIER

#4.b) process supplier and ask p_name:
def process_supplier(update: Update, context: CallbackContext) -> int:
    if context.user_data.get('supplier') == 'NEW':
        supplier = update.message.text.lower()
    else:
        #get from query:
        query = update.callback_query
        supplier = query.data
        tlog.info(supplier)
        query.edit_message_reply_markup(reply_markup=None)
        query.answer()
    #store in bot memory:
    context.user_data['supplier'] = supplier
    tlog.info(f"Letto produttore {supplier}.")
    #next message:
    msg = f"Segnato produttore {supplier}! Ora scrivimi il nome dettagliato del <b>prodotto</b>. Aggiungi tutte le info necessarie, es.:\n\n<i>Grintuss pediatric sciroppo 12 flaconcini</i>\n\nOppure scrivi /esci per uscire."
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode=ParseMode.HTML)
    return PROCESS_PNAME

#5) process p_name and ask_category:
def process_pname(update: Update, context: CallbackContext) -> int:
    #get prod name sent by user:
    p_name = update.message.text.lower()
    p_name = p_name.replace("'", "")
    #store in bot memory:
    context.user_data['p_name'] = p_name
    tlog.info(f"Letto nome prodotto {p_name}.")
    #next message:
    msg = f"Segnato nome {p_name}! Ora dimmi a quale <b>categoria</b> appartiene (es. cosmesi, alimentazione, ...).\n\nOppure scrivi /esci per uscire."
    #category picker:
    keyboard = bot_functions.inline_picker('Categoria')
    update.message.reply_text(msg, 
        parse_mode=ParseMode.HTML, 
        reply_markup=InlineKeyboardMarkup(keyboard))
    return PROCESS_CATEGORY


#6.a) new category:
def new_category(update: Update, context: CallbackContext) -> int:
    #get open query:
    query = update.callback_query
    choice = query.data
    #store choice:
    context.user_data['category'] = 'NEW'
    tlog.info(choice)
    #answer query:
    query.delete_message()
    query.answer()
    #ask new:
    msg = f"Scrivimi il nome della <b>nuova categoria</b>.\n\nOppure scrivi /esci per uscire."
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode=ParseMode.HTML)
    return PROCESS_CATEGORY

#6.b) process category and ask p_name:
def process_category(update: Update, context: CallbackContext) -> int:
    if context.user_data.get('category') == 'NEW':
        category = update.message.text.lower()
    else:
        #get from query:
        query = update.callback_query
        category = query.data
        tlog.info(category)
        query.edit_message_reply_markup(reply_markup=None)
        query.answer()
    #store in bot memory:
    context.user_data['category'] = category
    tlog.info(f"Letta categoria {category}.")
    #next message:
    msg = f"Segnata categoria {category}! Mi dici il <b>numero di pezzi</b> che hai in magazzino?\n\nScrivi solo la <i>cifra</i>, es. 1, 10, ...\n\nOppure scrivi /esci per uscire."
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode=ParseMode.HTML)
    return PROCESS_PIECES

#7) process pieces:
def process_pieces(update: Update, context: CallbackContext) -> int:
    #1) check caller function:
    to_edit = context.user_data.get('to_edit')
    if (to_edit == None) or (to_edit == 'Quantita'):
        #a) if pieces:
        try:
            pieces = int(update.message.text)
        except:
            msg = "Re-inviami soltanto il numero in cifre (es. 1, 10, ...).\n\nOppure scrivi /esci per uscire."
            update.message.reply_text(msg)
            return PROCESS_PIECES
        #store in bot memory:
        context.user_data['pieces'] = pieces
        tlog.info(f"Letti {pieces} pezzi.")
        msg = f"Segnato {pieces} pezzi. "
    else:
        #b) if to_edit (no pieces):
        mapping = {'Produttore': 'supplier', 'Nome': 'p_name', 'Categoria': 'category', 'Quantita': 'pieces'}
        context.user_data[mapping[to_edit]] = update.message.text.lower()
        context.user_data['to_edit'] = None
        msg = f"Aggiornato. "
    
    #prepare product recap:
    utts = {
        'p_code': int(context.user_data['p_code']),
        'supplier': context.user_data['supplier'],
        'p_name': context.user_data['p_name'],
        'category': context.user_data['category'],
        'pieces': int(context.user_data['pieces']),
    }
    msg = f"{msg}Ti invio il recap del prodotto da aggiungere:\n"+\
            f"- Codice: {utts['p_code']}\n"+\
            f"- Produttore: {utts['supplier']}\n"+\
            f"- Nome: {utts['p_name']}\n"+\
            f"- Categoria: {utts['category']}\n"+\
            f"- Numero di pezzi: {utts['pieces']}\n"+\
            f"\nPosso salvare nel magazzino?"
    keyboard = [[InlineKeyboardButton('Sì', callback_data='Sì'),
                InlineKeyboardButton('No', callback_data='No')]]
    update.message.reply_text(msg,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard))
    return SAVE


#6) process category and ask_quantity:
def save_to_db(update: Update, context: CallbackContext) -> int:
    #get open query:
    query = update.callback_query
    choice = query.data
    tlog.info(choice)
    query.edit_message_reply_markup(reply_markup=None)
    query.answer()
    err = False
    if choice == 'Sì':
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
        except:
            err = True
        
        if err == True or ret == -1:
            msg = f"C'è stato un problema col mio DB, ti chiedo scusa!"
            context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
            return CONV_END
        else:
            msg = f"Ti ho salvato il prodotto nel magazzino!\n\nVuoi che ti faccia qualche altra domanda per categorizzare meglio il prodotto?"
            keyboard = [[InlineKeyboardButton('Sì', callback_data='Sì'),
                        InlineKeyboardButton('No', callback_data='No')]]
            context.bot.send_message(chat_id=update.effective_chat.id, text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard))
            return CONV_END
    else:
        #trigger edit:
        keyboard = [[InlineKeyboardButton('Produttore', callback_data='Produttore'),
                InlineKeyboardButton('Nome', callback_data='Nome')],
                [InlineKeyboardButton('Categoria', callback_data='Categoria'),
                InlineKeyboardButton('Quantita', callback_data='Quantita')],
                [InlineKeyboardButton('Esci', callback_data='Esci')]]
        msg = f"Cosa vuoi modificare?"
        context.bot.send_message(chat_id=update.effective_chat.id, text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard))
        return ASK_REWRITE

def ask_rewrite(update: Update, context: CallbackContext) -> int:
    #get open query:
    query = update.callback_query
    choice = query.data
    tlog.info(choice)
    #if end:
    if choice == 'Esci':
        query.edit_message_reply_markup(reply_markup=None)
        query.answer()
        msg = f"Ok. A presto!"
        context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
        return CONV_END
    #else: prepare edit:
    context.user_data['to_edit'] = choice
    query.delete_message()
    query.answer()
    if choice == 'Quantita':
        msg = f"Riscrivi qui il <b>numero</b> corretto di pezzi (nota: solo cifre)."
    else:
        msg = f"Riscrivi qui il testo corretto per il campo <b>{choice}</b>"
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode=ParseMode.HTML)
    return PROCESS_PIECES

#CANCEL AND END:
def esci(update: Update, context: CallbackContext) -> int:
    msg = "Uscito. A presto!"
    update.message.reply_text(msg)
    return CONV_END


#GET DB VIEW IN PDF:
def prodotti(update: Update, context: CallbackContext) -> int:
    # try:
    conn, cursor = db_connect()
    Prodotti = db_interactor.get_view_prodotti(conn)
    conn.close()
    if Prodotti.empty == False:
        #build plt table:
        fig, ax =plt.subplots(figsize=(12,4))
        ax.axis('tight')
        ax.axis('off')
        ax.table(cellText=Prodotti.values,colLabels=Prodotti.columns,loc='center')
        #export table to pdf:
        filename = './telegram_support/data_cache/prodotti.pdf'
        pp = PdfPages(filename)
        pp.savefig(fig, bbox_inches='tight')
        pp.close()
        #send pdf:
        pdfdoc = open(filename, 'rb')
        chat_id=update.effective_chat.id
        return context.bot.send_document(chat_id, pdfdoc)
    # except:
    #     msg = f"C'è stato un problema col mio DB, ti chiedo scusa!"
    #     update.message.reply_text(msg)


#MAIN:
def main() -> None:
    #create the Updater and pass it the bot's token:
    updater = Updater(TOKEN, use_context=True)
    #get the dispatcher to register handlers:
    dispatcher = updater.dispatcher

    #command handlers:
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help))
    #dispatcher.add_handler(CommandHandler("prodotti", prodotti))

    #conversation handlers:
    #add new product ("/nuovo"):
    conv_handler = ConversationHandler(
        entry_points=[
                CommandHandler('nuovo', nuovo),
                MessageHandler(Filters.regex("^(Nuovo|nuovo)$|^Aggiungi nuovo$|^(Nuovo|nuovo) prodotto$|^Aggiungi nuovo prodotto$"), nuovo)],
        states={
            ASK_PCODE: [CallbackQueryHandler(ask_pcode, pattern='.*')],
            PROCESS_PCODE: [
                MessageHandler(Filters.photo, pcode_process_photo),
                MessageHandler(Filters.text, pcode_process_text)],
            PROCESS_SUPPLIER: [
                CallbackQueryHandler(new_supplier, pattern='^NUOVO$'),
                CallbackQueryHandler(process_supplier, pattern='.*'),
                MessageHandler(Filters.text, process_supplier)],
            PROCESS_PNAME: [
                MessageHandler(Filters.text, process_pname)],
            PROCESS_CATEGORY: [
                CallbackQueryHandler(new_category, pattern='^NUOVO$'),
                CallbackQueryHandler(process_category, pattern='.*'),
                MessageHandler(Filters.text, process_category)],
            PROCESS_PIECES: [MessageHandler(Filters.text, process_pieces)],
            SAVE: [CallbackQueryHandler(save_to_db, pattern='.*')],
            ASK_REWRITE: [CallbackQueryHandler(ask_rewrite, pattern='.*')],
        },
        fallbacks=[
            CommandHandler('esci', esci),
            MessageHandler(Filters.regex("^(Esci|Stop|Basta|Annulla)$"), esci)])
    dispatcher.add_handler(conv_handler)

    #message handlers:
    dispatcher.add_handler(MessageHandler(Filters.text, echo))

    #start polling:
    updater.start_polling()

    #idle:
    updater.idle()


if __name__ == '__main__':
    main()
