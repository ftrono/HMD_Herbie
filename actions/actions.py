from typing import Any, Text, Dict, List
from rasa_sdk import Tracker, Action, Action, ValidationAction, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from rasa_sdk.events import SlotSet, AllSlotsReset, FollowupAction
from globals import *
from db_tools import db_connect
from db_interaction import get_pieces, update_pieces, delete_ordlist, get_existing_ordlist, get_new_ordlist
from common_actions import is_int, is_affirmative, readable_date, disambiguate_prod, disambiguate_supplier, update_warehouse, read_ord_list, update_ord_list

#CUSTOM ACTIONS & FORMS VALIDATION:

#GLOBAL SLOTS VALIDATION:
#(when slots are used outside a form)
#class ValidatePredefinedSlots(ValidationAction):


#CUSTOM ACTIONS:
class ActionResetAllSlots(Action):
    def name(self) -> Text:
            return "action_reset_all_slots"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        return [AllSlotsReset()]


#Check pieces in DB and return if they are sufficient:
class ActionCheckWH(Action):
    def name(self) -> Text:
            return "action_check_wh"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        p_code = tracker.get_slot("p_code")
        print("CHECKING: ", p_code)
        if p_code != None:
            try:
                conn, cursor = db_connect()
                pieces = int(get_pieces(cursor, p_code))
                conn.close()
                if pieces > THRESHOLD_TO_ORD:
                    message = f"Hai {pieces} pezzi in magazzino."
                    dispatcher.utter_message(text=message)
                    return [SlotSet('need_order', False)]
                else:
                    if pieces == 0:
                        message = f"Non hai più pezzi rimasti in magazzino!"
                    elif pieces == 1:
                        message = f"Hai un solo pezzo rimasto in magazzino."
                    else:
                        message = f"Hai solo {pieces} pezzi rimasti in magazzino."
                    dispatcher.utter_message(text=message)
                    return [SlotSet('need_order', True)]
            except:
                print("DB connection error.")
                message = "C'è stato un problema con il mio database, ti chiedo scusa."
                dispatcher.utter_message(text=message)
            return []

class ActionAddToList(Action):
    def name(self) -> Text:
            return "action_add_to_list"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        print("AGGIUNGO ALLA LISTA")
        slots = tracker.current_slot_values()
        if slots['add_to_order'] == True:
            #store number of pieces to add, if said:
            if slots['pieces'] == None:
                slots['pieces'] = 1
            print("Pieces: ", slots['pieces'])
            '''
            #add to order list in DB:
            try:
                conn, cursor = db_connect()
                latest_code, _, _ = get_orderlist(conn, cursor, slots['supplier']) #####################
                if latest_code != None:
                    query = f"INSERT INTO ListeOrdini (CodiceOrd, CodiceProd, Quantità) VALUES ({latest_code}, '{slots['p_code']}', {slots['pieces']})"

                    ####### END UPDATE #######

                conn.close()
            except:
                print("DB connection error.")
                message = "C'è stato un problema con il mio database, ti chiedo scusa."
                dispatcher.utter_message(text=message)
                return [AllSlotsReset()]
            '''
            dispatcher.utter_message(response="utter_done")
        else:
            dispatcher.utter_message(response="utter_ok")
        dispatcher.utter_message(response="utter_available")
        return [AllSlotsReset()]


#For init_order_form:
class ActionAskUseExisting(Action):
    def name(self) -> Text:
            return "action_ask_use_existing"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        #get slots saved:
        supplier = tracker.get_slot("supplier")
        dispatcher.utter_message(response="utter_ready_to_order")
        slots = {}
        slots_set = []
        try:
            conn, cursor = db_connect()
            #check if an open list exists:
            slots['ord_code'], slots['ord_date'], slots['ord_list'], num_prods = get_existing_ordlist(conn, supplier)
            #if it exists:           
            if slots['ord_code'] != None:
                #prepare strings for message:
                num_str = f"{num_prods} prodotti"
                if num_prods == 1:
                    num_str = "un prodotto"
                read_date = readable_date(slots['ord_date'])
                message = f"Abbiamo già una lista aperta, modificata per ultimo {read_date}, con {num_str}. Continuiamo con questa?"
                dispatcher.utter_message(text=message)
                #prepare next slots (continue form):
                slots['use_existing'] = None
                if num_prods == 0:
                    slots['read'] = False
                else:
                    slots['read'] = None
            else:
                slots['ord_code'] = get_new_ordlist(conn, cursor, supplier)
                message = f"Ti ho creato una nuova lista!"
                dispatcher.utter_message(text=message)
                #can deactivate init_order form:
                slots['use_existing'] = False
                slots['read'] = False
                slots['requested_slot'] = None

            conn.close()
            #generate return:
            for key in slots.keys():
                slots_set.append(SlotSet(key, slots[key]))

        except:
            print("DB connection error.")
            message = "C'è stato un problema con il mio database, ti chiedo scusa."
            dispatcher.utter_message(text=message)

        return slots_set


#For order_form: read item in list:
class ActionAskQuantity(Action):
    def name(self) -> Text:
            return "action_ask_quantity"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        #get list and positional index in reading:
        ord_list = tracker.get_slot('ord_list')
        ind = tracker.get_slot('index')
        if ind == None:
            ind = 0
        #extract p_code and reading message:
        p_code, message = read_ord_list(ord_list, ind, read_quantity=False)
        dispatcher.utter_message(text=message)
        return [SlotSet('p_code', p_code)]


#FORMS VALIDATION:
#1. Warehouse update:
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
        
        slots = disambiguate_prod(tracker, dispatcher)
        return slots

    def validate_check(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> Dict[Text, Any]:

        slots = disambiguate_prod(tracker, dispatcher)
        return slots


#1. Warehouse update:
class ValidateWhUpdateForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_wh_update_form"

    def validate_p_code(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> Dict[Text, Any]:
        
        slots = disambiguate_prod(tracker, dispatcher)
        return slots

    def validate_check(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> Dict[Text, Any]:

        slots = disambiguate_prod(tracker, dispatcher)
        return slots

    def validate_variation(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> Dict[Text, Any]:

        variation = tracker.get_slot("variation")
        if variation != 'add' and variation != 'decrease':
            dispatcher.utter_message(response='utter_please_rephrase')
            variation = None
        return {'variation': variation}

    def validate_pieces(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> Dict[Text, Any]:

        slots = tracker.current_slot_values()
        slots['pieces'] = next(tracker.get_latest_entity_values("pieces"), None)
        if slots['pieces'] != None:
            #update warehouse and reset form:
            print("Ok", slots['variation'], slots['pieces'])
            slots = update_warehouse(tracker, dispatcher, slots)
        else:
            message = f"Mmm, non ho capito il numero di pezzi."
            dispatcher.utter_message(text=message)
            slots['pieces'] = None
        return slots


#3. make order:
#3.0. parent forker:
class ValidateInitOrderForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_init_order_form"

    def validate_s_text(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> Dict[Text, Any]:

        #find and disambiguate supplier:
        slots = disambiguate_supplier(tracker, dispatcher)
        return slots

    def validate_check(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> Dict[Text, Any]:

        #find and disambiguate supplier:
        slots = disambiguate_supplier(tracker, dispatcher)
        return slots

    def validate_use_existing(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> Dict[Text, Any]:

        #validate user intent:
        intent = tracker.latest_message['intent'].get('name')
        read = tracker.get_slot("read")
        slots = {}

        if intent == 'ask_read':
            #use existing list and read it first:
            print("Affermativo + leggi lista")
            dispatcher.utter_message(response="utter_ok")
            slots['use_existing'] = True
            slots['read'] = True   #skip next slot & end form
            slots['requested_slot'] = None

        elif intent == 'affirm' and read == False:
            #if use_existing list but it's empty: skip request to read:
            print("Affermativo + lista vuota")
            dispatcher.utter_message(response="utter_ok")
            slots['use_existing'] = True
            slots['requested_slot'] = None
        
        elif intent == 'affirm':
            #use existing list. Need to ask whether to read it or not:
            print("Affermativo")
            dispatcher.utter_message(response="utter_ok")
            slots['use_existing'] = True

        elif intent == 'deny' or intent == 'ask_new':
            #don't use existing list: discard it and create a new list:
            print("Negativo")
            dispatcher.utter_message(response="utter_ok")
            supplier = tracker.get_slot("supplier")
            ord_code = tracker.get_slot("ord_code")
            try:
                conn, cursor = db_connect()
                ret = delete_ordlist(conn, cursor, ord_code)
                slots['ord_code'] = get_new_ordlist(conn, cursor, supplier)
                conn.close()
                message = f"Ti ho creato una nuova lista per {supplier}, useremo questa!"
                dispatcher.utter_message(text=message)

            except:
                print("DB connection error.")
                message = "C'è stato un problema con il mio database, ti chiedo scusa."
                dispatcher.utter_message(text=message)

            #reset old slots + can deactivate init_order form:
            slots['ord_date'] = None
            slots['ord_list'] = None
            slots['use_existing'] = False
            slots['read'] = False   #skip next slot & end form

        else:
            message = "Mmm, non ho capito bene."
            dispatcher.utter_message(text=message)
            slots['use_existing'] = None
        
        return slots

    def validate_read(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> Dict[Text, Any]:

        read = is_affirmative(tracker, dispatcher)
        return {'read': read}


########################
#3.0. parent forker:
class ValidateReadOrderForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_read_order_form"

    def validate_quantity(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> Dict[Text, Any]:

        #validate user intent:
        intent = tracker.latest_message['intent'].get('name')

        #if stop:
        if intent == 'deny':
            print("Negativo")
            #fork: either remove prod or stop conversation
            dispatcher.utter_message(response="utter_ok")
            return False
        else:
            pieces = next(tracker.get_latest_entity_values("pieces"), None)
            if pieces != None:
                slots = tracker.current_slot_values()
                slots['pieces'] = pieces
                ord_list = update_ord_list(slots['ord_code'], slots['index'], slots['p_code'], slots['pieces'])
            else:
                message = "Mmm, non ho capito bene."
                dispatcher.utter_message(text=message)
                return None

    def validate_p_text(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> Dict[Text, Any]:

        #GET SUPPLIER SLOT AND PASS IT TO DISAMBIGUATE_PROD, IN PLACE OF =True !!!
        new_slots = disambiguate_prod(tracker, dispatcher, supplier=True)
        return new_slots

    def validate_check(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> Dict[Text, Any]:

        #GET SUPPLIER SLOT AND PASS IT TO DISAMBIGUATE_PROD, IN PLACE OF =True !!!
        new_slots = disambiguate_prod(tracker, dispatcher, supplier=True)
        return new_slots

    def validate_quantity(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> Dict[Text, Any]:

        utts = {}
        #extract needed info:
        utts['pieces'] = next(tracker.get_latest_entity_values("pieces"), None)
        utts['p_code'] = tracker.get_slot("p_code")
        print(utts['p_code'])

        #fallback 1:
        if utts['pieces'] == None:
            message = "Mmm, non ho capito bene."
            dispatcher.utter_message(text=message)
            return {"quantity": None, "pieces": None}

        #db extraction:
        if is_int(utts['pieces']) and int(utts['pieces']) > 0:
            print("Write", utts['pieces'])
            try:
                conn, cursor = db_connect()
                ret = update_pieces(conn, cursor, utts) ##############
                conn.close()
                if ret == 0:
                    if int(utts['pieces']) == 1:
                        message = "Segnato un pezzo."
                    else:
                        message = f"Segnàti {utts['pieces']} pezzi"
                else:
                    message = "C'è stato un problema con il mio database, ti chiedo scusa."
            except:
                print("DB connection error")
                message = "C'è stato un problema con il mio database, ti chiedo scusa."
            dispatcher.utter_message(text=message)
            return {"quantity": None, "pieces": None, 'requested_slot': None} ###################
        else:
            print(utts['var'], utts['pieces'])
            message = f"Mmm, non ho capito il numero di pezzi."
            dispatcher.utter_message(text=message)
            return {"quantity": None, "pieces": None}

    def validate_next(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> Dict[Text, Any]:

        next_one = is_affirmative(tracker, dispatcher)
        if next_one == False:
            dispatcher.utter_message(response="utter_available")
        return {'next': next_one}
