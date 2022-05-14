from typing import Any, Text, Dict, List
from rasa_sdk import Tracker, Action, Action, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, FollowupAction
from globals import *
from database.db_tools import db_connect, db_disconnect
import database.db_interactor as db_interactor
import actions.commons as commons
import actions.products as products
import actions.orders as orders
import actions.views as views


#CUSTOM ACTIONS & FORMS VALIDATION

#CUSTOM ACTIONS:
#All -> reset all slots:
class ActionResetAllSlots(Action):
    def name(self) -> Text:
            return "action_reset_all_slots"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        slots_set = commons.reset_all(tracker)
        return slots_set


#Form Reset -> reset recurrent slots for forms:
class ActionResetFormSlots(Action):
    def name(self) -> Text:
            return "action_reset_form_slots"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        to_delete = ['p_code', 'pieces', 'keep', 'add_sugg', 'variation']
        slots_set = []
        for sname in to_delete:
            slots_set.append(SlotSet(sname, None))
        return slots_set


#adapt greet depending on the time of the day:
class ActionUtterGreet(Action):
    def name(self) -> Text:
            return "action_utter_greet"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        message = commons.adapt_greeting()
        dispatcher.utter_message(text=message)
        return []


#Views -> Send view via tBot:
class ActionGuideUser(Action):
    def name(self) -> Text:
            return "action_guide_user"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        #disambiguate current case based on the slots populated:
        p_code = tracker.get_slot("p_code")
        supplier = tracker.get_slot("supplier")
        if p_code:
            #utter guidance for conv "product":
            message = "Puoi chiedermi le quantità disponibili in magazzino, oppure di darti informazioni sul prodotto, come prezzo di listino, categoria e aliquota IVA, se è un dispositivo medico, se contiene glutine, lattosio o zucchero, o se è vegano."
            dispatcher.utter_message(text=message)
        elif supplier:
            #utter guidance for conv "supplier":
            message = "Puoi chiedermi di cercarti i prodotti in esaurimento, o di inviarti la vista delle giacenze. Puoi anche chiedermi di preparare o di continuare un ordine, di trovarti o confermare l'ultima lista ordini e di inviartela via Bot."
            dispatcher.utter_message(text=message)
        else:
            #utter general guidance on main commands:
            dispatcher.utter_message(response='utter_guidance')
        return []


#PRODUCTS:
#Product Info:
class ActionUtterProdInfo(Action):
    def name(self) -> Text:
            return "action_utter_prodinfo"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        slots = tracker.current_slot_values()
        if slots['p_code'] == None:
            message = f"Chiedimi di trovare un prodotto, potrò risponderti subito dopo."
        else:
            message = products.read_prodinfo(slots)
        dispatcher.utter_message(text=message)
        return []

class ActionUtterPrice(Action):
    def name(self) -> Text:
            return "action_utter_price"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        price = tracker.get_slot("price")
        if price == None:
            message = f"Chiedimi di trovare un prodotto, potrò risponderti subito dopo."
        else:
            message = f"Il prezzo di listino è {commons.readable_price(price)}."
        dispatcher.utter_message(text=message)
        return []

class ActionUtterCatVat(Action):
    def name(self) -> Text:
            return "action_utter_cat_vat"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        category = tracker.get_slot("category")
        vat = tracker.get_slot("vat")
        if category == None or vat == None:
            message = f"Chiedimi di trovare un prodotto, potrò risponderti subito dopo."
        else:
            message = products.read_cat_vat(category, vat)
        dispatcher.utter_message(text=message)
        return []

class ActionUtterDispMedico(Action):
    def name(self) -> Text:
            return "action_utter_dispmedico"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        dispmedico = tracker.get_slot("dispmedico")
        if dispmedico == None:
            message = f"Chiedimi di trovare un prodotto, potrò risponderti subito dopo."
        else:
            message = products.read_dispmedico(dispmedico)
        dispatcher.utter_message(text=message)
        return []

class ActionUtterCompatibility(Action):
    def name(self) -> Text:
            return "action_utter_compatibility"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        vegan = tracker.get_slot("vegan")
        nolactose = tracker.get_slot("no_lactose")
        nogluten = tracker.get_slot("no_gluten")
        nosugar = tracker.get_slot("no_sugar")
        if vegan == None or nolactose == None or nogluten == None or nosugar == None:
            message = f"Chiedimi di trovare un prodotto, potrò risponderti subito dopo."
        else:
            message = products.read_compatibility(vegan, nolactose, nogluten, nosugar)
        dispatcher.utter_message(text=message)
        return []

class ActionUtterVegan(Action):
    def name(self) -> Text:
            return "action_utter_vegan"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        vegan = tracker.get_slot("vegan")
        if vegan == None:
            message = f"Chiedimi di trovare un prodotto, potrò risponderti subito dopo."
        else:
            message = products.read_vegan(vegan)
        dispatcher.utter_message(text=message)
        return []

class ActionUtterNoLactose(Action):
    def name(self) -> Text:
            return "action_utter_nolactose"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        vegan = tracker.get_slot("vegan")
        nolactose = tracker.get_slot("no_lactose")
        if vegan == None or nolactose == None:
            message = f"Chiedimi di trovare un prodotto, potrò risponderti subito dopo."
        else:
            message = products.read_nolactose(vegan, nolactose)
        dispatcher.utter_message(text=message)
        return []

class ActionUtterNoGluten(Action):
    def name(self) -> Text:
            return "action_utter_nogluten"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        nogluten = tracker.get_slot("no_gluten")
        if nogluten == None:
            message = f"Chiedimi di trovare un prodotto, potrò risponderti subito dopo."
        else:
            message = products.read_nogluten(nogluten)
        dispatcher.utter_message(text=message)
        return []

class ActionUtterNoSugar(Action):
    def name(self) -> Text:
            return "action_utter_nosugar"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        nosugar = tracker.get_slot("no_sugar")
        if nosugar == None:
            message = f"Chiedimi di trovare un prodotto, potrò risponderti subito dopo."
        else:
            message = products.read_nosugar(nosugar)
        dispatcher.utter_message(text=message)
        return []


#Quantities -> check pieces in DB:
class ActionCheckQuantity(Action):
    def name(self) -> Text:
            return "action_check_quantity"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        p_code = tracker.get_slot("p_code")
        if p_code != None:
            try:
                pieces = int(tracker.get_slot("cur_quantity"))
            except:
                elog.info("DB connection error.")
                message = "C'è stato un problema con il mio database, ti chiedo scusa."
                dispatcher.utter_message(text=message)
                return [SlotSet('fail', True)]
            if pieces > THRESHOLD_TO_ORD:
                message = f"Hai {pieces} pezzi in magazzino."
                dispatcher.utter_message(text=message)
            else:
                if pieces == 0:
                    message = f"Non hai più pezzi rimasti in magazzino. Potrebbe servirti presto!"
                elif pieces == 1:
                    message = f"Hai un solo pezzo rimasto in magazzino. Potrebbe servirti presto!"
                else:
                    message = f"Hai solo {pieces} pezzi rimasti in magazzino. Potrebbe servirti presto!"
                dispatcher.utter_message(text=message)
            dispatcher.utter_message(response='utter_ask_add_to_order')
        return []


#Quantities -> add product to the next order list:
class ActionAddToList(Action):
    def name(self) -> Text:
            return "action_add_to_list"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        err = False
        slots = tracker.current_slot_values()
        #add to order list in DB:
        try:
            conn, cursor = db_connect()
            #get an open order list (existing or new):
            ord_code, _ = orders.get_open_order(conn, cursor, slots['supplier'])
            #add product to list:
            ret = db_interactor.edit_ord_list(conn, cursor, ord_code, slots['p_code'], pieces=1, write_mode=True)
            db_disconnect(conn, cursor)
        except:
            err = True

        if err == True or ret == -1:
            elog.info("DB connection error.")
            message = "C'è stato un problema con il mio database, ti chiedo scusa."
            dispatcher.utter_message(text=message)
            return [SlotSet('fail', True)]
        else:
            #product added:
            message = "Segnato nella prossima lista ordini!"
            dispatcher.utter_message(text=message)
        return []


#SUPPLIER / ORDERS:
#Create Order -> get latest order list from DB or create a new one:
class ActionGetOrdList(Action):
    def name(self) -> Text:
            return "action_get_ordlist"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        #get slots saved:
        supplier = tracker.get_slot("supplier")
        if supplier == None:
            message = "Chiedimi di trovare un produttore. Potrò risponderti subito dopo!"
            dispatcher.utter_message(text=message)
            return []
        else:
            slots = {}
            try:
                conn, cursor = db_connect()
                #check if an open list exists:
                slots['ord_code'], slots['ord_date'], slots['ord_list'], num_prods = db_interactor.get_json_ordlist(conn, supplier)

                #if no open lists or empty open list -> create new list:
                if num_prods == 0:
                    if slots['ord_code'] != None:
                        db_interactor.delete_ordlist(slots['ord_code'], conn, cursor)
                    slots['ord_code'] = db_interactor.get_new_ordlist(conn, cursor, supplier)
                    message = f"Ti ho appena creato una nuova lista!"
                    dispatcher.utter_message(text=message)
                    slots['new_list'] = True

                #load open list:
                else:
                    #prepare strings for message:
                    num_str = f"{num_prods} prodotti"
                    if num_prods == 1:
                        num_str = "un prodotto"
                    read_date = commons.readable_date(slots['ord_date'])
                    message = f"Ti ho trovato l'ultima lista aperta, modificata per ultimo {read_date}, con {num_str}."
                    dispatcher.utter_message(text=message)
                    slots['new_list'] = False

                db_disconnect(conn, cursor)

            except:
                elog.info("DB connection error.")
                message = "C'è stato un problema con il mio database, ti chiedo scusa."
                dispatcher.utter_message(text=message)
                slots['fail'] = True
            
            slots_set = commons.convert_to_slotset(slots)
            return slots_set


#Create Order -> create suggestion list:
class ActionGetSuggestionList(Action):
    def name(self) -> Text:
            return "action_get_suggestion_list"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        #get slots saved:
        slots = tracker.current_slot_values()
        #extract JSON list:
        try:
            conn, cursor = db_connect()
            if slots['ord_code'] == None:
                slots['ord_code'], slots['new_list'] = orders.get_open_order(conn, cursor, slots['supplier'])
            slots['ord_list'], num_prods = db_interactor.get_suggestion_list(conn, slots['supplier'], slots['ord_code'])
            db_disconnect(conn, cursor)
            #if extracted suggestion list empty:
            if slots['ord_list'] == None:
                slots['found'] = False
                message = f"Non ho trovato altri prodotti di {slots['supplier']} con meno di {THRESHOLD_TO_ORD} pezzi!"
                dispatcher.utter_message(text=message)
                #end:
                slots_set = commons.convert_to_slotset(slots)
                return slots_set
            #else: trigger start read:
            else:
                slots['found'] = True
                if num_prods == 1:
                    num_str = "un solo prodotto"
                    start_str = ""
                else:
                    num_str = f"{num_prods} prodotti"
                    start_str = " Per ogni prodotto, dimmi se ordinarlo o ignorarlo e, nel caso, quanti pezzi vuoi ordinare!"
                message = f"Ti ho trovato {num_str} di {slots['supplier']} con meno di {THRESHOLD_TO_ORD} pezzi.{start_str}"
                dispatcher.utter_message(text=message)
        except:
            elog.info("DB connection error.")
            message = "C'è stato un problema con il mio database, ti chiedo scusa."
            dispatcher.utter_message(text=message)
            slots['fail'] = True
        
        slots_set = commons.convert_to_slotset(slots)
        return slots_set


#Create Order -> Read item in list and ask keep:
class ActionAskKeep(Action):
    def name(self) -> Text:
            return "action_ask_keep"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        #get JSON list to read:
        ord_list = tracker.get_slot('ord_list')
        #extract p_code and read message:
        slots = orders.read_ord_list(dispatcher, ord_list)
        if slots['p_code'] != None:
            dispatcher.utter_message(response='utter_ask_keep_piece')
        
        slots_set = commons.convert_to_slotset(slots)
        return slots_set


#Create Order -> Read item in list and ask keep:
class ActionAskAddSugg(Action):
    def name(self) -> Text:
            return "action_ask_add_sugg"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        #get slots saved:
        slots = tracker.current_slot_values()
        
        #2) read next prod in JSON list: extract p_code and read message:
        slots = orders.read_ord_list(dispatcher, slots['ord_list'], suggest_mode=True)
        if slots['p_code'] != None:
            dispatcher.utter_message(response='utter_ask_pieces')
        
        slots_set = commons.convert_to_slotset(slots)
        return slots_set


#Create Order -> Get total cost of an order:
class ActionUtterTotOrderCost(Action):
    def name(self) -> Text:
            return "action_utter_tot_ordcost"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        codiceord = tracker.get_slot("ord_code")
        if codiceord == None:
            message = f"Chiedimi di trovare una lista ordini, potrò risponderti subito dopo."
        else:
            tot_cost = orders.tot_ord_cost(codiceord)
            if tot_cost == 0:
                message = f"La lista è vuota al momento!"
            else:
                message = f"Il costo totale stimato per l'ordine è {commons.readable_price(tot_cost)}."
        dispatcher.utter_message(text=message)
        return []

#Create Order -> Mark order as definitive:
class ActionMarkDefinitive(Action):
    def name(self) -> Text:
            return "action_mark_definitive"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        slots = tracker.current_slot_values()
        if slots['ord_code'] == None:
            message = f"Chiedimi di trovare una lista ordini, potrò risponderti subito dopo."
        else:
            ret = db_interactor.mark_definitive(slots['ord_code'])
            if ret == 0:
                message = f"Ok, ti ho confermato l'ordine per {slots['supplier']} come definitivo. "
                #also send final list via Telegram:
                ret, _ = views.get_vista(caller='lista', filter=slots['ord_code'])
                if ret == 0:
                    message = f"{message}Ti ho inviato la lista pronta via Telegram! "
                #final guidance:
                message = f"{message}Quando l'ordine ti verrà consegnato, chiedimi di registrarti la consegna, ti inserirò i prodotti arrivati in automatico."
            else:
                message = f"C'è stato un problema col mio magazzino, ti chiedo scusa!"
                return [SlotSet('fail', True)]
        dispatcher.utter_message(text=message)
        return []


#Warehouse -> Check if there are closed orders. Else, utter default ask_what:
class ActionProactiveCheck(Action):
    def name(self) -> Text:
            return "action_proactive_check"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(response='utter_opened_warehouse')
        num_closed = db_interactor.check_closed()
        if num_closed > 0:
            #proactive ask for open order:
            message = f"Ti è stato consegnato un ordine?"
            dispatcher.utter_message(text=message)
            return [SlotSet('pending_delivery', True)]
        else:
            #go on:
            return [SlotSet('pending_delivery', None)]


#Warehouse -> Ask confirm register delivered:
class ActionConfirmDelivered(Action):
    def name(self) -> Text:
            return "action_confirm_delivered"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        slots = tracker.current_slot_values()
        #get latest closed order for the supplier:
        try:
            conn, cursor = db_connect()
            closed_code, closed_date, closed_list, num_prods = db_interactor.get_json_ordlist(conn, slots['supplier'], closed=True)
            db_disconnect(conn, cursor)
            if closed_code == None:
                message = f"Non ho trovato ordini chiusi per {slots['supplier']}."
                dispatcher.utter_message(text=message)
                return [SlotSet('found', None)]
            else:
                tot_pieces = "un pezzo" if num_prods == 1 else f"{num_prods} pezzi"
                message = f"Abbiamo chiuso la lista {commons.readable_date(closed_date)}, contiene {tot_pieces} in totale: ti aggiornerò le quantità in magazzino di ogni prodotto in lista. Confermi?"
                dispatcher.utter_message(text=message)
                return [SlotSet('found', True), SlotSet('closed_code', closed_code), SlotSet('closed_list', closed_list)]
        except Exception as e:
            elog.error(f"action_confirm_delivered(): Unable to check DB. {e}")
            message = f"C'è stato un problema, ti chiedo scusa!"
            dispatcher.utter_message(text=message)
            return [SlotSet('fail', True)]


#Warehouse -> Register closed order as delivered and update warehouse:
class ActionRegisterDelivered(Action):
    def name(self) -> Text:
            return "action_register_delivered"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        slots = tracker.current_slot_values()
        #1) send list via Bot and delete closed list from DB:
        ret_send, _ = views.get_vista(caller='lista', filter=slots['closed_code'])
        ret_del = db_interactor.delete_ordlist(slots['closed_code'])
        if ret_del == 0:
            #2) update wh:
            ret_upd = db_interactor.register_delivered(slots['closed_code'], slots['closed_list'])
            if ret_upd == 0:
                message = f"Registrato! Ti ho aggiornato le quantità di ogni prodotto in lista nel magazzino."
                message = f"{message} Ti ho inviato l'aggiornamento su Telegram come dettaglio." if ret_send == 0 else ""
                dispatcher.utter_message(text=message)
                return [SlotSet('closed_code', None), SlotSet('closed_list', None)]
            else:
                message = f"C'è stato un problema, ti chiedo scusa! Chiedimi di aggiornare le giacenze, dovremo aggiornare le quantità un prodotto alla volta."
                dispatcher.utter_message(text=message)
                elog.error(f"action_register_delivered(): DB error. Closed list deleted but wh not updated.")
                return [SlotSet('fail', True)]
        else:
            message = f"C'è stato un problema, ti chiedo scusa!"
            dispatcher.utter_message(text=message)
            elog.error(f"action_register_delivered(): DB error. Closed list not deleted.")
            return [SlotSet('fail', True)]


#Views -> Send view via tBot:
class ActionSendView(Action):
    def name(self) -> Text:
            return "action_send_view"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        #disambiguate current case based on the slots populated:
        codiceord = tracker.get_slot("ord_code")
        supplier = tracker.get_slot("supplier")
        #priority order:
        if codiceord and supplier:
            _, message = views.get_vista(caller='lista', filter=codiceord)
        elif supplier:
            _, message = views.get_vista(caller='prodotti', filter=supplier)
        else:
            _, message = views.get_vista(caller='prodotti')
        dispatcher.utter_message(text=message)
        return []


#FORMS VALIDATION:
#Finders -> find a product in DB:
class ValidateFindProdForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_find_prod_form"

    def validate_p_code(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> Dict[Text, Any]:
        
        slots = commons.disambiguate_prod(tracker, dispatcher)
        return slots


#Finders -> find a supplier in DB:
class ValidateFindSupplierForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_find_supplier_form"

    def validate_supplier(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> Dict[Text, Any]:

        #find and disambiguate supplier:
        slots = commons.disambiguate_supplier(tracker, dispatcher)
        return slots


#Loopers -> register quantities variations:
class ValidateVariationsForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_variations_form"

    def validate_p_code(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> Dict[Text, Any]:
        
        slots = commons.disambiguate_prod(tracker, dispatcher, pieces=True)
        return slots

    def validate_variation(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> Dict[Text, Any]:

        slots = tracker.current_slot_values()
        #check if skip:
        intent = tracker.latest_message['intent'].get('name')
        if intent == 'deny':
            dispatcher.utter_message(response='utter_skip')
            elog.info(f"Skip")
            slots = commons.reset_and_goto(slots, del_slots=['p_code', 'p_name', 'supplier', 'cur_quantity', 'variation'], req_slot='p_code')
        else:
            #custom pieces entity extractor:
            text = tracker.latest_message.get("text")
            slots['pieces'] = commons.extract_pieces(text)
            elog.info(f"Extracted pieces: {slots['pieces']}")
            #slots check:
            if (slots['variation'] != 'add' and slots['variation'] != 'decrease') or (slots['pieces'] == None):
                message = f"Mmm, non ho capito. Dimmi 'aggiungi' o 'togli' e il numero di pezzi."
                dispatcher.utter_message(text=message)
                slots['variation'] = None
                slots['pieces'] = None
            else:
                #update warehouse and reset form:
                elog.info(f"Ok, {slots['variation']}, {slots['pieces']}")
                slots = commons.update_warehouse(dispatcher, slots)
        return slots


#Loopers -> read order list:
class ValidateReadOrderForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_read_order_form"

    def validate_keep(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> Dict[Text, Any]:

        slots = tracker.current_slot_values()
        #custom pieces entity extractor:
        text = tracker.latest_message.get("text")
        slots['pieces'] = commons.extract_pieces(text)
        elog.info(f"Extracted pieces: {slots['pieces']}")

        #cases:
        #a) not understood:
        if slots['keep'] != True and slots['keep'] != False:
            dispatcher.utter_message(response='utter_please_rephrase')
            slots['keep'] = None
            return slots

        #b) no pieces given by user:
        elif slots['pieces'] == None:
            slots['pieces'] = 0
        
        #update warehouse and reset form:
        elog.info(f"Ok, {slots['keep']}, {slots['pieces']}")
        slots = orders.update_ord_list(dispatcher, slots)
        return slots


#Loopers -> write order list:
class ValidateWriteOrderForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_write_order_form"

    def validate_p_code(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> Dict[Text, Any]:

        supplier = tracker.get_slot("supplier")
        slots = commons.disambiguate_prod(tracker, dispatcher, supplier=supplier, pieces=True)
        return slots

    def validate_pieces(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> Dict[Text, Any]:

        slots = tracker.current_slot_values()
        #check if skip:
        intent = tracker.latest_message['intent'].get('name')
        if intent == 'deny':
            dispatcher.utter_message(response='utter_skip')
            elog.info(f"Skip")
            slots = commons.reset_and_goto(slots, del_slots=['p_code', 'p_name', 'pieces', 'add_sugg'], req_slot='p_code')
        else:
            #custom pieces entity extractor:
            text = tracker.latest_message.get("text")
            slots['pieces'] = commons.extract_pieces(text)
            elog.info(f"Extracted pieces: {slots['pieces']}")
            if slots['pieces'] != None:
                #update warehouse and reset form:
                elog.info(f"Ok, {slots['p_code']}, {slots['pieces']}")
                slots = orders.write_ord_list(dispatcher, slots, next_slot='p_code')
            else:
                message = f"Mmm, non ho capito bene."
                dispatcher.utter_message(text=message)
                slots['pieces'] = None
        return slots


#Loopers -> suggest order list:
class ValidateSuggestOrderForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_suggest_order_form"

    def validate_add_sugg(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> Dict[Text, Any]:

        slots = tracker.current_slot_values()
        #custom pieces entity extractor:
        text = tracker.latest_message.get("text")
        slots['pieces'] = commons.extract_pieces(text)
        elog.info(f"Extracted pieces: {slots['pieces']}")

        #cases:
        #a) if no pieces given by user:
        if slots['pieces'] == None:
            #a.1) if intent is ignore product:
            if slots['add_sugg'] == False:
                dispatcher.utter_message(response='utter_skip')
                #update JSON reading list only (no DB):
                slots['ord_list'] = orders.update_reading_list(slots['ord_list'])
                #if empty list:
                if slots['ord_list'] == None:
                    message = f"Non ho trovato altri prodotti di {slots['supplier']} con meno di {THRESHOLD_TO_ORD} pezzi!"
                    dispatcher.utter_message(text=message)
                    next_slot = None
                else:
                    dispatcher.utter_message(response='utter_ask_next')
                    next_slot = 'add_sugg'
                #reset/deactivate form, keeping stored only the slots to be used forward:
                slots = commons.reset_and_goto(slots, del_slots=['p_code', 'p_name', 'pieces', 'add_sugg'], req_slot=next_slot)

            else:
                #a.2) not understood:
                message = f"Mmm, non ho capito bene."
                dispatcher.utter_message(text=message)
                slots['add_sugg'] = None
                slots['pieces'] = None
                return slots

        #b) update order list in DB, JSON reading list and reset form:
        else:
            elog.info(f"Ok, {slots['add_sugg']}, {slots['pieces']}")
            slots = orders.write_ord_list(dispatcher, slots, next_slot='add_sugg', update_json=True)
        return slots
