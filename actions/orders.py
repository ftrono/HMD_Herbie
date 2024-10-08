import random
from globals import *
from database.db_tools import db_connect, db_disconnect
import database.db_interactor as db_interactor
import database.db_export as db_export
import actions.commons as commons

#ORDERS:
# - get_open_order()
# - read_ord_list()
# - update_reading_list()
# - update_ord_list()
# - write_ord_list()
# - tot_ord_cost()

#get an open order (either existing or new):
def get_open_order(conn, cursor, supplier):
    ord_code = None
    err = False
    new_list = False
    #check if an open list exists:
    try:
        ord_code, _, _, _ = db_interactor.get_json_ordlist(conn, supplier)
    except:
        err = True
    #if no open lists -> create new list:
    if ord_code == None or err == True:
        ord_code = db_interactor.get_new_ordlist(conn, cursor, supplier)
        new_list = True
    return ord_code, new_list


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
            str_q = f"hai un solo pezzo in magazzino." if slots['cur_quantity'] == 1 else f"hai {slots['cur_quantity']} pezzi in magazzino."
        else:
            giacenza = int(OrdList['giacenza'].iloc[0])
            str_q = f"in magazzino hai un solo pezzo," if giacenza == 1 else f"in magazzino hai {giacenza} pezzi,"
            str_q = f"{str_q} abbiamo segnato un solo pezzo in lista." if slots['cur_quantity'] == 1 else f"{str_q} abbiamo segnato {slots['cur_quantity']} pezzi in lista."
        #utter:
        message = f"{slots['p_name']}: {str_q}"
        dispatcher.utter_message(text=message)
    else:
        #empty_list:
        message = f"Ho esaurito la lista!"
        dispatcher.utter_message(text=message)
        #deactivate form and keep stored only the slots to be used forward:
        slots = commons.reset_and_goto(slots, del_slots=['keep', 'pieces', 'p_code', 'p_name', 'ord_list', 'add_sugg'], req_slot=None)
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
                kept = [
                    "Tenuto!",
                    "Tengo!",
                    "Ok, mantengo!",
                    "Ok, tengo così!"
                ]
                message = kept[random.randint(0, len(kept))]
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
        message = "C'è stato un problema con il mio database, ti chiedo scusa. Riproviamo!"
        dispatcher.utter_message(text=message)
        elog.error("update_ord_list(): DB interaction error.")

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
    slots = commons.reset_and_goto(slots, del_slots=['keep', 'pieces', 'p_code', 'p_name', 'add_sugg'], req_slot=next_slot)
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
        message = "C'è stato un problema con il mio database, ti chiedo scusa. Riprova da capo!"
        dispatcher.utter_message(text=message)
        elog.error("write_ord_list(): DB interaction error.")
        #reset:
        slots = commons.reset_and_goto(slots, del_slots=['p_code', 'p_name', 'pieces', 'add_sugg'], req_slot=next_slot)
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
    slots = commons.reset_and_goto(slots, del_slots=['p_code', 'p_name', 'pieces', 'add_sugg'], req_slot=next_slot)
    return slots


#get total cost of an order list:
def tot_ord_cost(codiceord):
    tot_cost = 0
    OrdList = db_export.get_view_listaordine(codiceord=codiceord)
    if OrdList.empty == False:
        tot_costs = []
        for ind in OrdList.index:
            #unit costs +VAT:
            cost = OrdList['costo'].iloc[ind]
            cost = cost + (cost * (OrdList['aliquota'].iloc[ind]/100))
            #total cost:
            totcost = cost * OrdList['quantita'].iloc[ind]
            tot_costs.append(totcost)
        tot_cost = sum(tot_costs)
    return tot_cost

