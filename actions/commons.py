from rasa_sdk.events import SlotSet
from globals import *
from database.db_tools import db_connect
import database.db_interactor as db_interactor
from utils import readable_date

#COMMONS:
#Python functions that are used across multiple custom actions / forms:
# - convert_to_slotset()
# - reset_and_goto()
# - disambiguate_prod()
# - disambiguate_supplier()
# - update_warehouse()
# - read_ord_list()
# - update_reading_list()
# - update_ord_list()
# - write_ord_list()


#generate return (convert slots dict to SlotSet list):
def convert_to_slotset(slots):
    slots_set = []
    for key in slots.keys():
        slots_set.append(SlotSet(key, slots[key]))
    return slots_set


#reset all slots and go to req_slot:
def reset_and_goto(slots, req_slot=None, keep_slots=None, del_slots=None):
    '''
    params:
    - slots = dict
    - req_slot = str (None)
    - keep_slots = list of strings (None)
    '''
    #1) save slot values to keep:
    if keep_slots:
        buf = {} #buffer
        for sname in keep_slots:
            buf[sname] = slots[sname]
    
    #2) reset:
    #a. selected slots:
    if del_slots:
        for sname in del_slots:
            slots[sname] = None
    #b. all slots:
    else:
        for key in slots.keys():
            slots[key] = None

    #3) restore slots to keep:
    if keep_slots:
        for sname in keep_slots:
            slots[sname] = buf[sname]

    #4) set new requested_slot (either req_slot or None):
    slots['requested_slot'] = req_slot
    return slots


#Disambiguate product reference from DB:
def disambiguate_prod(tracker, dispatcher, supplier=None):
    #extract needed info:
    str1 = "nome"
    suppstr = ""
        
    print(tracker.get_slot("p_code"))
    utts = {
        'p_code': next(tracker.get_latest_entity_values("p_code"), None), 
        'p_text': str(tracker.get_slot("p_code")), #first value of p_code is populated "from_text"
        'supplier': supplier if supplier else None
        }
    print(utts)

    #fallback a: no info:
    if utts['p_code'] == None and utts['p_text'] == None:
        message = f"Mmm, mi manca qualche informazione. Puoi leggermi il codice a barre, oppure dirmi produttore e nome, o anche solo il nome!"
        dispatcher.utter_message(text=message)
        slots = {"p_code": None}
        return slots

    elif utts['p_code'] != None:
        #entity p_code, if found, has priority over full intent text:
        utts['p_code'] = str(utts['p_code']).lower()
        str1 = "codice"
    
    #db extraction:
    try:
        conn, cursor = db_connect()
        resp = db_interactor.get_prodinfo(conn, utts)
        conn.close()
    except:
        resp = []
    
    #fallback b: not found:
    if resp == []:
        if supplier:
            suppstr = f"di {supplier} "
        message = f"Non ho trovato nessun prodotto {suppstr}con questo {str1}."
        dispatcher.utter_message(text=message)
        slots = {"p_code": None}
        return slots

    #fallback c: multiple found:
    elif len(resp) > 1:
        message = f"Ho trovato più di un prodotto simile:"
        for prod in resp:
            message = f"{message}\nDi {prod['supplier']}, {prod['p_name']}."
        dispatcher.utter_message(text=message)
        slots = {"p_code": None}
        return slots

    #success: match found:
    else:
        prod = resp[0]
        message = f"Trovato! Di {prod['supplier']}, {prod['p_name']}."
        dispatcher.utter_message(text=message)
        slots = {"p_code": str(prod['p_code']), "p_name": str(prod['p_name']), "supplier": str(prod['supplier'])}
        return slots


#Get supplier reference from DB:
def disambiguate_supplier(tracker, dispatcher):
    #extract s_text:
    s_text = next(tracker.get_latest_entity_values("supplier"), None)
    if s_text == None:
        s_text = str(tracker.get_slot("supplier")) #first value of supplier is populated "from_text"
    else:
        s_text = str(s_text)
    
    #process supplier name:
    s_text = s_text.lower()
    print(s_text)

    #db extraction:
    try:
        conn, cursor = db_connect()   
        resp = db_interactor.get_supplier(conn, s_text)
        conn.close()
    except:
        resp = []
    
    #fallback: not found:
    if resp == []:
        message = f"Non ho trovato nessun produttore con questo nome!"
        dispatcher.utter_message(text=message)
        return {"supplier": None}

    #fallback: multiple found:
    elif len(resp) > 1:
        message = f"Ho trovato più di un produttore con un nome simile:\n"
        for suppl in resp:
            message = f"{message}{suppl}\n"
        dispatcher.utter_message(text=message)
        return {"supplier": None}

    #ok: unique:
    else:
        suppl = resp[0]
        return {"supplier": suppl}


#Stock info: update quantity of a product in DB:
def update_warehouse(dispatcher, slots):
    try:
        conn, cursor = db_connect()
        #check lower boundary:
        if slots['variation'] == 'decrease':
            floor = db_interactor.get_pieces(cursor, slots['p_code'])

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
                message = f"Ho trovato solo {str1}."
                dispatcher.utter_message(text=message)
                slots['pieces'] = floor

        #update DB:
        ret = db_interactor.update_pieces(conn, cursor, slots)
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


#READ order list:
def read_ord_list(dispatcher, ord_list, suggest_mode=False):
    slots = {}
    #unpack JSON string to DataFrame:
    OrdList = json.loads(ord_list)
    OrdList = pd.DataFrame(OrdList)
    if OrdList.empty == False:
        #read first row:
        slots['p_code'] = str(OrdList['CodiceProd'].iloc[0])
        slots['p_name'] = str(OrdList['Nome'].iloc[0])
        slots['cur_quantity'] = int(OrdList['Quantita'].iloc[0])
        #build string:
        if suggest_mode == True:
            str_have = "hai "
        else:
            str_have = ""
        if slots['cur_quantity'] == 1:
            str_q = f"un pezzo."
        else:
            str_q = f"{slots['cur_quantity']} pezzi."
        #utter:
        message = f"{slots['p_name']}, {str_have}{str_q}"
        dispatcher.utter_message(text=message)
    else:
        #empty_list:
        message = f"Ho esaurito la lista!"
        dispatcher.utter_message(text=message)
        #deactivate form and keep stored only the slots to be used forward:
        slots = reset_and_goto(slots, req_slot=None, del_slots=['keep', 'pieces', 'p_code', 'p_name', 'ord_list', 'add_sugg'])
    return slots


#Update JSON reading list (slot):
def update_reading_list(ord_list):
    #unpack JSON:
    OrdList = json.loads(ord_list)
    OrdList = pd.DataFrame(OrdList)
    #delete first row:
    OrdList = OrdList.tail(OrdList.shape[0] -1)
    if OrdList.empty == True:
        #empty_list:
        ord_list = None
    else:
        #re-pack updated JSON:
        ord_list = OrdList.to_dict()
        ord_list = json.dumps(ord_list)
    return ord_list


#UPDATE order list:
def update_ord_list(dispatcher, slots):
    err = False
    ret = 0
    next_slot = 'keep'
    slots['pieces'] = int(slots['pieces'])

    #1) update order list in DB:
    try:
        conn, cursor = db_connect()
        #cases:
        if slots['pieces'] == 0:
            if slots['keep'] == False:
                #delete row from DB:
                message = f"Ok, ti ho rimosso {slots['p_name']} dalla lista."
                ret = db_interactor.edit_ord_list(conn, cursor, slots['ord_code'], slots['p_code'], slots['pieces'])
            else:
                #no change to DB:
                message = f"Mantengo il prodotto!"
        else:
            if slots['pieces'] == 1:
                message = f"Ti ho segnato un pezzo."
            else:
                message = f"Ti ho segnato {slots['pieces']} pezzi totali."
            #replace quantity to DB:
            ret = db_interactor.edit_ord_list(conn, cursor, slots['ord_code'], slots['p_code'], slots['pieces'])
        conn.close()
    except:
        err = True

    #2) if error:
    if err == True or ret == -1:
        print("DB connection error.")
        message = "C'è stato un problema con il mio database, ti chiedo scusa. Riproviamo!"
        dispatcher.utter_message(text=message)

    else:
        #3) utter update message:
        dispatcher.utter_message(text=message)

        #4) update JSON reading list:
        slots['ord_list'] = update_reading_list(slots['ord_list'])
        if slots['ord_list'] == None:
            #empty_list:
            message = f"Ho esaurito la lista da leggere!"
            dispatcher.utter_message(text=message)
            next_slot = None
        else:
            dispatcher.utter_message(response='utter_ask_next')

    #5) restart form, keeping stored only the slots to be used forward:
    slots = reset_and_goto(slots, req_slot=next_slot, del_slots=['keep', 'pieces', 'p_code', 'p_name', 'add_sugg'])
    return slots


#WRITE order list:
def write_ord_list(dispatcher, slots, next_slot, update_json=False):
    err = False
    #1) update order list in DB:
    try:
        conn, cursor = db_connect()
        ret = db_interactor.edit_ord_list(conn, cursor, slots['ord_code'], slots['p_code'], slots['pieces'], write_mode=True)
        conn.close()
    except:
        err = True
    
    #2) if error:
    if err == True or ret == -1:
        print("DB connection error.")
        message = "C'è stato un problema con il mio database, ti chiedo scusa. Riprova da capo!"
        dispatcher.utter_message(text=message)
    else:
        #3) utter update message:
        if slots['pieces'] == 1:
            message = f"Un pezzo, segnato!"
        else:
            message = f"{slots['pieces']} pezzi segnàti!"
        dispatcher.utter_message(text=message)
    
    #4) (only if suggestion form): update JSON reading list:
    if update_json == True:
        slots['ord_list'] = update_reading_list(slots['ord_list'])
        if slots['ord_list'] == None:
            #empty_list:
            message = f"Non ho trovato altri prodotti di {slots['supplier']} con meno di {THRESHOLD_TO_ORD} pezzi!"
            dispatcher.utter_message(text=message)
            #reset form:
            next_slot = None

    #5) ask next:
    if next_slot != None:
        dispatcher.utter_message(response='utter_ask_next')
    
    #6) restart form, keeping stored only the slots to be used forward:
    slots = reset_and_goto(slots, req_slot=next_slot, del_slots=['p_code', 'p_name', 'pieces', 'add_sugg'])
    return slots
