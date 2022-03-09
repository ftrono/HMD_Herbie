from typing import Any, Text, Dict, List
from datetime import datetime, date
import pytz
from globals import *
from db_tools import db_connect
from db_interaction import get_prodinfo, get_supplier, get_pieces, update_pieces

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
def check_deactivate(tracker, dispatcher, slots=None):
    deact = False
    intent = tracker.latest_message['intent'].get('name')
    print(f"Intent: {intent}")
    if not slots:
        slots = tracker.current_slot_values()
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
    str1 = "nome"
    utts = {
        'p_code': next(tracker.get_latest_entity_values("p_code"), None), 
        'p_text': str(tracker.latest_message.get("text")).lower(),
        'supplier': supplier if supplier else None
        }
    print(utts)

    #fallback a: no info:
    if utts['p_code'] == None and utts['p_text'] == None:
        message = f"Mmm, mi manca qualche informazione. Puoi leggermi il codice a barre, oppure dirmi produttore e nome, o anche solo il nome!"
        dispatcher.utter_message(text=message)
        slots = {"p_code": None, "check": None}
        return slots

    elif utts['p_code'] != None:
        #entity p_code, if found, has priority over intent text:
        utts['p_code'] = str(utts['p_code']).lower()
        str1 = "codice"
    
    #db extraction:
    try:
        conn, cursor = db_connect()   
        resp = get_prodinfo(conn, utts)
        conn.close()
    except:
        resp = []
    
    #fallback b: not found:
    if resp == []:
        message = f"Non ho trovato nessun prodotto con questo " + str1 + "."
        dispatcher.utter_message(text=message)
        slots = {"p_code": None, "check": None}
        return slots

    #fallback c: multiple found:
    elif len(resp) > 1:
        message = f"Ho trovato più di un prodotto simile:"
        for prod in resp:
            message = message + "\nDi " + prod['supplier'] + ", " + prod['p_name'] + "."
        dispatcher.utter_message(text=message)
        dispatcher.utter_message(response="utter_specify")
        slots = {"p_code": 0, "check": None}
        return slots

    #success: match found:
    else:
        prod = resp[0]
        message = f"Trovato! Di {prod['supplier']}, {prod['p_name']}."
        dispatcher.utter_message(text=message)
        slots = {"p_code": str(prod['p_code']), "check": True, "p_name": str(prod['p_name']), "supplier": str(prod['supplier'])}
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
        return {"s_text": False, "check": None}

    #fallback: multiple found:
    elif len(resp) > 1:
        message = f"Ho trovato più di un produttore con un nome simile:\n"
        for suppl in resp:
            message = message + suppl + "\n"
        dispatcher.utter_message(text=message)
        dispatcher.utter_message(response="utter_specify")
        return {"s_text": True, "check": None}

    #ok: unique:
    else:
        suppl = resp[0]
        return {"s_text": True, "check": True, "supplier": suppl}


def update_warehouse(tracker, dispatcher, slots):
    try:
        conn, cursor = db_connect()
        #check lower boundary:
        if slots['variation'] == 'decrease':
            floor = get_pieces(cursor, slots['p_code'])

            if floor == 0:
                message = f"La tua scorta era a zero, non ho potuto fare nulla. Proviamo con un altro prodotto!"
                dispatcher.utter_message(text=message)
                #empty slots and restart form:
                ret_slots = reset_and_goto(slots, req_slot='p_code')
                return ret_slots

            if floor < int(slots['pieces']):
                if floor == 1:
                    str1 = "un pezzo"
                else:
                    str1 = f"{floor} pezzi"
                message = "Ho trovato solo " + str1 + "."
                dispatcher.utter_message(text=message)
                slots['pieces'] = floor

        #update DB:
        ret = update_pieces(conn, cursor, slots)
        conn.close()
    except:
        ret = -1
        print("DB connection error")
    
    if int(slots['pieces']) == 1:
        str1 = "un pezzo"
    else:
        str1 = f"{slots['pieces']} pezzi"

    if ret == 0 and slots['variation'] == 'add':
        message = f"Ti ho aggiunto {str1} a {slots['p_name']} di {slots['supplier']}."
        dispatcher.utter_message(text=message)
        dispatcher.utter_message(response='utter_ask_next')

    elif ret == 0 and slots['variation'] == 'decrease':
        message = f"Ti ho rimosso {str1} a {slots['p_name']} di {slots['supplier']}."
        dispatcher.utter_message(text=message)
        dispatcher.utter_message(response='utter_ask_next')

    else:
        message = "C'è stato un problema con il mio database, ti chiedo scusa. Riprova al prossimo turno!"
        dispatcher.utter_message(text=message)
    #empty slots and restart form:
    ret_slots = reset_and_goto(slots, req_slot='p_code')
    return ret_slots


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
