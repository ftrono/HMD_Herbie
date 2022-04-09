from rasa_sdk.events import SlotSet
from globals import *
from database.db_tools import db_connect, db_disconnect
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
def reset_and_goto(slots, del_slots, req_slot=None):
    '''
    params:
    - del_slots = list of strings
    - req_slot = str (None)
    '''
    #reset selected slots:
    for sname in del_slots:
        slots[sname] = None

    #set new requested_slot (either req_slot or None):
    slots['requested_slot'] = req_slot
    return slots


#Disambiguate product reference from DB:
def disambiguate_prod(tracker, dispatcher, supplier=None, pieces=None):
    #p_code -> from entity (numbers only):
    p_code = next(tracker.get_latest_entity_values("p_code"), None)
    #p_text -> the intent text is temporarily saved by Rasa into "p_code" slot before validation:
    p_text = str(tracker.get_slot("p_code")) 
    supplier = supplier if supplier else None
    print(p_code, p_text, supplier)

    #fallback a: no info:
    if p_code == None and p_text == None:
        message = f"Mmm, mi manca qualche informazione. Puoi leggermi il codice a barre, oppure dirmi produttore e nome, o anche solo il nome!"
        dispatcher.utter_message(text=message)
        slots = {"p_code": None}
        return slots
    
    #db extraction:
    Matches = db_interactor.match_product(p_code, p_text, supplier)
    
    #fallback b: not found:
    if Matches.empty == True:
        suppstr = f"di {supplier} " if supplier else ""
        given = "codice" if p_code != None else "nome"
        message = f"Non ho trovato nessun prodotto {suppstr}con questo {given}."
        dispatcher.utter_message(text=message)
        slots = {"p_code": None}
        return slots

    #fallback c: multiple found:
    elif len(Matches.index) > 1:
        message = f"Ho trovato più di un prodotto simile:"
        for ind in Matches.index:
            message = f"{message}\nDi {Matches['produttore'].iloc[ind]}, {Matches['nome'].iloc[ind]}."
        dispatcher.utter_message(text=message)
        slots = {"p_code": None}
        return slots

    #success: match found:
    else:
        p_code = Matches['codiceprod'].iloc[0]
        supplier = Matches['produttore'].iloc[0]
        p_name = Matches['nome'].iloc[0]
        quantity = Matches['quantita'].iloc[0]
        slots = {"p_code": str(p_code), "p_name": p_name, "supplier": supplier, "cur_quantity": str(quantity)}
        message = f"Trovato! Di {supplier}, {p_name}."
        #additional info on pieces:
        if pieces == True:
            if quantity == 1:
                message = f"{message} Hai un solo pezzo."
            else:
                message = f"{message} Hai {quantity} pezzi."
        #utter message:
        dispatcher.utter_message(text=message)
        return slots


#Get supplier reference from DB:
def disambiguate_supplier(tracker, dispatcher):
    #s_text -> the intent text is temporarily saved by Rasa into "supplier" slot before validation:
    supplier = tracker.get_slot("supplier").lower()
    print(supplier)

    #db extraction:
    results = db_interactor.match_supplier(supplier)
    
    #fallback: not found:
    if results == []:
        message = f"Non ho trovato nessun produttore con questo nome!"
        dispatcher.utter_message(text=message)
        return {"supplier": None}

    #fallback: multiple found:
    elif len(results) > 1:
        message = f"Ho trovato più di un produttore con un nome simile:\n"
        for supplier in results:
            message = f"{message}{supplier}\n"
        dispatcher.utter_message(text=message)
        return {"supplier": None}

    #ok: unique:
    else:
        return {"supplier": results[0]}


#Stock info: update quantity of a product in DB:
def update_warehouse(dispatcher, slots):
    #check lower boundary:
    if slots['variation'] == 'decrease':
        floor = int(slots['cur_quantity'])
        #zero:
        if floor == 0:
            message = f"La tua scorta era a zero, non ho potuto fare nulla. Proviamo con un altro prodotto!"
            dispatcher.utter_message(text=message)
            #empty slots and restart form:
            ret_slots = reset_and_goto(slots, del_slots=['p_code', 'p_name', 'supplier', 'cur_quantity', 'variation'], req_slot='p_code')
            return ret_slots
        #less pieces:
        if floor < int(slots['pieces']):
            found = "un pezzo" if floor == 1 else f"{floor} pezzi"
            message = f"Ho trovato solo {found}."
            dispatcher.utter_message(text=message)
            slots['pieces'] = floor
    
    #update DB:
    ret = db_interactor.update_pieces(slots)
    var = "un pezzo" if int(slots['pieces']) == 1 else f"{slots['pieces']} pezzi"

    if ret == 0 and slots['variation'] == 'add':
        message = f"Ti ho aggiunto {var} a {slots['p_name']} di {slots['supplier']}."
        dispatcher.utter_message(text=message)
        dispatcher.utter_message(response='utter_ask_next')

    elif ret == 0 and slots['variation'] == 'decrease':
        message = f"Ti ho rimosso {var} a {slots['p_name']} di {slots['supplier']}."
        dispatcher.utter_message(text=message)
        dispatcher.utter_message(response='utter_ask_next')

    else:
        message = "C'è stato un problema con il mio database, ti chiedo scusa. Riprova al prossimo turno!"
        dispatcher.utter_message(text=message)
    #empty slots and restart form:
    ret_slots = reset_and_goto(slots, del_slots=['p_code', 'p_name', 'supplier', 'cur_quantity', 'variation'], req_slot='p_code')
    return ret_slots


#READ order list:
def read_ord_list(dispatcher, ord_list, suggest_mode=False):
    slots = {}
    #unpack JSON string to DataFrame:
    OrdList = json.loads(ord_list)
    OrdList = pd.DataFrame(OrdList)
    if OrdList.empty == False:
        #read first row:
        slots['p_code'] = str(OrdList['codiceprod'].iloc[0])
        slots['p_name'] = str(OrdList['nome'].iloc[0])
        slots['cur_quantity'] = int(OrdList['quantita'].iloc[0])
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
        slots = reset_and_goto(slots, del_slots=['keep', 'pieces', 'p_code', 'p_name', 'ord_list', 'add_sugg'], req_slot=None)
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
        db_disconnect(conn, cursor)
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
    slots = reset_and_goto(slots, del_slots=['keep', 'pieces', 'p_code', 'p_name', 'add_sugg'], req_slot=next_slot)
    return slots


#WRITE order list:
def write_ord_list(dispatcher, slots, next_slot, update_json=False):
    err = False
    #1) update order list in DB:
    try:
        conn, cursor = db_connect()
        ret = db_interactor.edit_ord_list(conn, cursor, slots['ord_code'], slots['p_code'], slots['pieces'], write_mode=True)
        db_disconnect(conn, cursor)
    except:
        err = True
    
    #2) if error:
    if err == True or ret == -1:
        print("DB connection error.")
        message = "C'è stato un problema con il mio database, ti chiedo scusa. Riprova da capo!"
        dispatcher.utter_message(text=message)
        #reset:
        slots = reset_and_goto(slots, del_slots=['p_code', 'p_name', 'pieces', 'add_sugg'], req_slot=next_slot)
        return slots
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
    slots = reset_and_goto(slots, del_slots=['p_code', 'p_name', 'pieces', 'add_sugg'], req_slot=next_slot)
    return slots
