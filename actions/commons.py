from rasa_sdk.events import SlotSet
import random
from globals import *
import database.db_interactor as db_interactor

#COMMONS:
#Python functions that are used across multiple custom actions / forms:
# - convert_to_slotset()
# - reset_and_goto()
# - reset_all()
# - adapt_greeting()
# - readable_date()
# - check_intent()
# - disambiguate_prod()
# - disambiguate_supplier()
# - update_warehouse()


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


#reset all slots (for custom actions):
def reset_all(tracker):
    slots = tracker.current_slot_values()
    slots_set = []
    for sname in slots.keys():
        slots_set.append(SlotSet(sname, None))
    return slots_set


#answer "ciao" or adapted greet depending on random prob:
def adapt_greeting():
    pick = random.randint(0, 10)
    if pick <= 5:
        #simple greet:
        message = "Ciao!"
    else:
        #get current time of the day:
        now = datetime.now(pytz.timezone('Europe/Rome'))
        hour = int(now.hour)
        #adapt greet:
        if hour < 13:
            message = f"Buongiorno!"
        elif hour >= 13 and hour < 18:
            message = "Buon pomeriggio!"
        else:
            message = "Buonasera!"
    return message


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


#check if user is referring to a previous match or has changed his mind:
def check_intent(tracker, dispatcher, p_text):
    intent = tracker.latest_message['intent'].get('name')
    pos = 0
    #if ordinal and previous list:
    if intent == 'inform_ordinal':
        p_text = p_text.replace("'", " ")
        toks = p_text.split()
        #check position:
        for tok in toks:
            if len(tok) > 1:
                tok = tok[:-1]
                if tok == 'prim' or tok == 'un':
                    pos = 1
                    break
                elif tok == 'second' or tok == 'du':
                    pos = 2
                    break
                elif tok == 'terz' or tok == 'tr':
                    pos = 3
                    break
                elif tok == 'ultim':
                    pos = -1
                    break
    return pos


#Disambiguate product reference from DB:
def disambiguate_prod(tracker, dispatcher, supplier=None, pieces=None):
    #p_text -> the intent text is temporarily saved by Rasa into "p_code" slot before validation:
    p_text = str(tracker.get_slot("p_code")) 
    supplier = supplier if supplier else None
    elog.info(f"{p_text}, {supplier}")

    #fallback a: no info:
    if p_text == None:
        message = f"Mmm, mi manca qualche informazione. Dimmi produttore e nome del prodotto, o anche solo il nome!"
        dispatcher.utter_message(text=message)
        slots = {"p_code": None}
        return slots
    
    #check if user uttered an ordinal:
    matches = tracker.get_slot("matches")
    pos = check_intent(tracker, dispatcher, p_text)
    #a) if yes:
    if matches != None and pos != 0:
        #unpack JSON string to DataFrame:
        Matches = json.loads(matches)
        Matches = pd.DataFrame(Matches)
        #get the reference row and proceed to edit info / add info:
        if pos != -1:
            pos = pos-1
        Matches = Matches.iloc[[pos]]
        Matches.reset_index(drop=True, inplace=True)

    #b) else -> extract from DB:
    else:
        Matches = db_interactor.match_product(p_text, supplier)
    
        #fallback b: not found:
        if Matches.empty == True:
            suppstr = f"di {supplier} " if supplier else ""
            message = f"Non ho trovato nessun prodotto {suppstr}con questo nome."
            dispatcher.utter_message(text=message)
            slots = {"p_code": None, "matches": None}
            return slots

        #fallback c: multiple found:
        elif len(Matches.index) > 1:
            message = f"Ecco cosa ho trovato:"
            for ind in Matches.index:
                message = f"{message}\nDi {Matches['produttore'].iloc[ind]}, {Matches['nome'].iloc[ind]}."
            message = f"{message} Puoi dirmi se è uno di questi o riprovare."
            dispatcher.utter_message(text=message)
            #pack matches list to JSON:
            matches = Matches.to_dict()
            matches = json.dumps(matches)
            #ret slots:
            slots = {"p_code": None, "matches": matches}
            return slots

    #common success: match found:
    p_code = Matches['codiceprod'].iloc[0]
    supplier = Matches['produttore'].iloc[0]
    p_name = Matches['nome'].iloc[0]
    quantity = Matches['quantita'].iloc[0]

    #purchase cost:
    cost = Matches['prezzo'].iloc[0] - (Matches['prezzo'].iloc[0] * (Matches['scontomedio'].iloc[0]/100))
    cost = cost + (cost * (Matches['aliquota'].iloc[0]/100))
    tot_cost = cost * quantity

    slots = {
        "matches": None, 
        "p_code": str(p_code), 
        "supplier": supplier, 
        "p_name": p_name, 
        "cur_quantity": str(quantity), 
        "category": Matches['categoria'].iloc[0], 
        "price": str(Matches['prezzo'].iloc[0]), 
        "discount": str(Matches['scontomedio'].iloc[0]), 
        "vat": str(int(Matches['aliquota'].iloc[0])), 
        "cost": str(cost),
        "tot_cost": str(tot_cost), 
        "tot_value": str(Matches['valoretotale'].iloc[0]), 
        "vegan": 'true' if Matches['vegano'].iloc[0] == True else 'false', 
        "no_lactose": 'true' if Matches['senzalattosio'].iloc[0] else 'false', 
        "no_gluten": 'true' if Matches['senzaglutine'].iloc[0] else 'false', 
        "no_sugar": 'true' if Matches['senzazucchero'].iloc[0] else 'false'
        }
    
    #utter message:
    message = f"Ok, di {supplier}, {p_name}."
    if pieces == True:
        if quantity == 1:
            message = f"{message} Hai un solo pezzo."
        else:
            message = f"{message} Hai {quantity} pezzi."
    dispatcher.utter_message(text=message)
    return slots


#Get supplier reference from DB:
def disambiguate_supplier(tracker, dispatcher):
    #s_text -> the intent text is temporarily saved by Rasa into "supplier" slot before validation:
    supplier = tracker.get_slot("supplier").lower()
    elog.info(supplier)

    #db extraction:
    results = db_interactor.match_supplier(supplier)
    
    #fallback: not found:
    if results == []:
        message = f"Non ho trovato nessun produttore con questo nome!"
        dispatcher.utter_message(text=message)
        return {"supplier": None}

    #fallback: multiple found:
    elif len(results) > 1:
        message = f"Ecco cosa ho trovato:\n"
        for supplier in results:
            message = f"{message}{supplier}\n"
        dispatcher.utter_message(text=message)
        return {"supplier": None}

    #ok: unique:
    else:
        supplier = results[0]
        message = f"Ok, {supplier}!"
        dispatcher.utter_message(text=message)
        return {"supplier": supplier}


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
        message = f"Ti ho aggiunto {var}!"
        dispatcher.utter_message(text=message)
        dispatcher.utter_message(response='utter_ask_next')

    elif ret == 0 and slots['variation'] == 'decrease':
        message = f"Ti ho rimosso {var}!"
        dispatcher.utter_message(text=message)
        dispatcher.utter_message(response='utter_ask_next')

    else:
        message = "C'è stato un problema con il mio database, ti chiedo scusa. Riprova!"
        dispatcher.utter_message(text=message)
    #empty slots and restart form:
    ret_slots = reset_and_goto(slots, del_slots=['p_code', 'p_name', 'supplier', 'cur_quantity', 'variation'], req_slot='p_code')
    return ret_slots
