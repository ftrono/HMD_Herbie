from typing import Any, Text, Dict, List
from datetime import datetime, date
import pytz
from globals import *
from db_tools import db_connect
from db_interaction import get_prodinfo, get_supplier, get_pieces

#DB DIALOG INTERFACES:
#Interface functions that are used across multiple forms.

#Check if a string is an integer:
def is_int(string: Text) -> bool:
    try:
        int(string)
        return True
    except ValueError:
        return False


def is_affirmative(tracker, dispatcher):
    #validate user intent:
    intent = tracker.latest_message['intent'].get('name')

    if intent == 'affirm':
        print("Affermativo")
        dispatcher.utter_message(response="utter_ok")
        return True

    elif intent == 'deny':
        print("Negativo")
        dispatcher.utter_message(response="utter_ok")
        return False

    else:
        message = "Mmm, non ho capito bene."
        dispatcher.utter_message(text=message)
        return None


#reset all slots and go to req_slot:
def reset_and_goto(slots, req_slot=None):
    for key in slots.keys():
        slots[key] = None
    #deactivate form:
    slots['requested_slot'] = req_slot
    return slots


#stop form & reset:
def check_deactivate(tracker, dispatcher, slots):
    deact = False
    intent = tracker.latest_message['intent'].get('name')
    print(f"Intent: {intent}")
    #stop check:
    if intent == 'stop':
        dispatcher.utter_message(response='utter_ok')
        dispatcher.utter_message(response='utter_available')
        #reset all slots and deactivate:
        reset_and_goto(slots)
        deact = True
    return deact, slots


#convert date to readable:
def readable_date(datestr):
    #orig date (format: '%Y-%m-%d'):
    comps = datestr.split('-')
    date_orig = date(int(comps[0]), int(comps[1]), int(comps[2]))
    mon = MONTHS[int(comps[1])-1]
    read_date = f"{int(comps[2])} {mon} {comps[0]}"

    #today:
    td = datetime.now(pytz.timezone('Europe/Rome'))
    td = td.strftime('%Y-%m-%d')
    comps_td = td.split('-')
    date_today = date(int(comps_td[0]), int(comps_td[1]), int(comps_td[2]))

    #datedif (in number of days):
    datedif = (date_today-date_orig).days

    #message:
    if datedif == 0:
        read_str = f"oggi"
    elif datedif == 1:
        read_str = f"ieri"
    elif datedif > 1 and datedif <= 15:
        read_str = f"{datedif} giorni fa, in data {read_date}"
    else:
        read_str = f"in data {read_date}"

    return read_str


#Disambiguate product reference from DB:
def disambiguate_prod(tracker, dispatcher, supplier=None):
    #extract needed info:
    utts = {
        'p_code': next(tracker.get_latest_entity_values("p_code"), None), 
        'p_text': str(tracker.latest_message.get("text")).lower(),
        'supplier': supplier if supplier else None
        }
    print(utts)

    #fallback:
    if utts['p_code'] == None and utts['p_text'] == None:
        message = f"Mmm, mi manca qualche informazione. Puoi leggermi il codice a barre, oppure dirmi il nome del prodotto e il produttore!"
        dispatcher.utter_message(text=message)
        slots = {"p_text": 'ok', "check": None}
        return slots

    elif utts['p_code'] != None:
        #p_code has priority:
        utts['p_code'] = str(utts['p_code']).lower()
    
    #db extraction:
    try:
        conn, cursor = db_connect()   
        resp = get_prodinfo(conn, utts)
        conn.close()
    except:
        resp = []
    
    #fallback: not found:
    if resp == []:
        if utts['p_code'] != None:
            str1 = "codice"
        else:
            str1 = "nome"
        message = f"Non ho trovato nessun prodotto con questo " + str1 + "."
        dispatcher.utter_message(text=message)
        dispatcher.utter_message(response="utter_repeat")
        slots = {"p_text": 'ok', "check": None}
        return slots

    #fallback: multiple found:
    elif len(resp) > 1:
        message = f"Ho trovato più di un prodotto simile:"
        for prod in resp:
            message = message + "\nDi " + prod['supplier'] + ", " + prod['p_name'] + "."
        dispatcher.utter_message(text=message)
        dispatcher.utter_message(response="utter_specify")
        slots = {"p_text": 'ok', "check": None}
        return slots

    #fallback: not found:
    else:
        prod = resp[0]
        message = f"Trovato! Di {prod['supplier']}, {prod['p_name']}."
        dispatcher.utter_message(text=message)
        slots = {"p_text": 'ok', "check": True, "p_code": str(prod['p_code']), "p_name": str(prod['p_name']), "supplier": str(prod['supplier'])}
        return slots


#Get supplier reference from DB:
def disambiguate_supplier(tracker, dispatcher):
    #extract s_text:
    s_text = next(tracker.get_latest_entity_values("s_text"), None)
    if s_text == None:
        s_text = tracker.latest_message.get("text")
    
    #process supplier name:
    s_text = s_text.lower()
    print(s_text)

    #db extraction:
    try:
        conn, cursor = db_connect()   
        resp = get_supplier(conn, s_text)
        conn.close()
    except:
        resp = []
    
    #fallback: not found:
    if resp == []:
        message = f"Non ho trovato nessun produttore con questo nome!"
        dispatcher.utter_message(text=message)
        dispatcher.utter_message(response="utter_repeat")
        return {"s_text": 'ok', "s_check": None}

    #fallback: multiple found:
    elif len(resp) > 1:
        message = f"Ho trovato più di un produttore con un nome simile:\n"
        for suppl in resp:
            message = message + suppl + "\n"
        dispatcher.utter_message(text=message)
        dispatcher.utter_message(response="utter_specify")
        return {"s_text": 'ok', "s_check": None}

    #ok: unique:
    else:
        suppl = resp[0]
        return {"s_text": 'ok', "s_check": True, "supplier": suppl}


#Check pieces in DB and return if they are sufficient:
def check_giacenza(dispatcher, p_code):
    try:
        conn, cursor = db_connect()
        pieces = int(get_pieces(cursor, p_code))
        conn.close()
        if pieces > THRESHOLD_TO_ORD:
            message = f"Hai {pieces} pezzi in magazzino."
            dispatcher.utter_message(text=message)
            return True
        else:
            if pieces == 0:
                message = f"Non hai più pezzi rimasti in magazzino!"
            elif pieces == 1:
                message = f"Hai un solo pezzo rimasto in magazzino."
            else:
                message = f"Hai solo {pieces} pezzi rimasti in magazzino."
            dispatcher.utter_message(text=message)
            return False
    except:
        print("DB connection error.")
        message = "C'è stato un problema con il mio database, ti chiedo scusa."
        dispatcher.utter_message(text=message)
    return None


#read order list:
def read_ord_list(ord_list, ind, read_quantity=True):
    #unpack JSON string to DataFrame:
    OrdList = json.loads(ord_list)
    OrdList = pd.DataFrame(OrdList)
    #extract info:
    try:
        p_code = str(OrdList['CodiceProd'].iloc[ind])
        p_name = str(OrdList['Nome'].iloc[ind])
        if read_quantity == True:
            quantity = str(OrdList['Quantità'].iloc[ind])
            if quantity == 1:
                str_q = f", un pezzo."
            else:
                str_q = f", {quantity} pezzi."
        else:
            str_q = ""
        #compose message:
        message = f"{p_name}{str_q}"
    except:
        p_code = None
        message = f"Ho esaurito la lista!"
    return p_code, message


#read order list:
def update_ord_list(ord_list, ind, read_quantity=True):
    #unpack JSON string to DataFrame:
    OrdList = json.loads(ord_list)
    OrdList = pd.DataFrame(OrdList)
    #extract info:
    try:
        p_code = str(OrdList['CodiceProd'].iloc[ind])
        p_name = str(OrdList['Nome'].iloc[ind])
        if read_quantity == True:
            quantity = str(OrdList['Quantità'].iloc[ind])
            if quantity == 1:
                str_q = f", un pezzo."
            else:
                str_q = f", {quantity} pezzi."
        else:
            str_q = ""
        #compose message:
        message = f"{p_name}{str_q}"
    except:
        p_code = None
        message = f"Ho esaurito la lista!"
    return p_code, message
