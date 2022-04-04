from typing import Any, Text, Dict, List
from rasa_sdk import Tracker, Action, Action, FormValidationAction, ValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from rasa_sdk.events import SlotSet, AllSlotsReset, FollowupAction
from globals import *
from database.db_tools import db_connect
import database.db_interactor as db_interactor
import actions.commons as commons
import utils


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

        return [AllSlotsReset()]


#Create Order -> reset recurrent slots for order preparation:
class ActionResetOrdSlots(Action):
    def name(self) -> Text:
            return "action_reset_ord_slots"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        to_delete = ['p_code', 'pieces', 'keep', 'add_sugg']
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

        message = utils.adapt_greeting()
        dispatcher.utter_message(text=message)
        return []


#Stock Info -> check pieces in DB and return need_order T/F:
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
                pieces = int(db_interactor.get_pieces(cursor, p_code))
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
            return [SlotSet('fail', True)]


#Stock Info -> add product to the next order list:
class ActionAddToList(Action):
    def name(self) -> Text:
            return "action_add_to_list"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        err = False
        slots = tracker.current_slot_values()
        if slots['add_to_order'] == True:
            #store number of pieces to add, if said:
            if slots['pieces'] == None:
                slots['pieces'] = 1
                message = "Segnato nella prossima lista ordini!"
            else:
                message = f"Segnàti {slots['pieces']} pezzi nella prossima lista ordini!"
            print("Pieces: ", slots['pieces'])

            #add to order list in DB:
            try:
                conn, cursor = db_connect()
                #check if an open list exists:
                ord_code, _, _, _ = db_interactor.get_existing_ordlist(conn, slots['supplier'])
                #if no open lists -> create new list:
                if ord_code == None:
                    ord_code = db_interactor.get_new_ordlist(conn, cursor, slots['supplier'])
                #add product to list:
                ret = db_interactor.edit_ord_list(conn, cursor, ord_code, slots['p_code'], slots['pieces'], write_mode=True)
            except:
                err = True

            if err == True or ret == -1:
                print("DB connection error.")
                message = "C'è stato un problema con il mio database, ti chiedo scusa."
                dispatcher.utter_message(text=message)
                return [SlotSet('fail', True)]
            else:
                #product added:
                dispatcher.utter_message(text=message)
        else:
            dispatcher.utter_message(response="utter_ok")
        dispatcher.utter_message(response="utter_available")
        return [AllSlotsReset()]


#Create Order -> get latest order list from DB:
class ActionGetOrdList(Action):
    def name(self) -> Text:
            return "action_get_ordlist"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        #get slots saved:
        supplier = tracker.get_slot("supplier")
        dispatcher.utter_message(response="utter_ready_to_order")
        slots = {}
        try:
            conn, cursor = db_connect()
            #check if an open list exists:
            slots['ord_code'], slots['ord_date'], slots['ord_list'], num_prods = db_interactor.get_existing_ordlist(conn, supplier)

            #if no open lists -> create new list:
            if slots['ord_code'] == None:
                slots['ord_code'] = db_interactor.get_new_ordlist(conn, cursor, supplier)
                message = f"Ti ho creato una nuova lista!"
                dispatcher.utter_message(text=message)
                slots['new_list'] = True
                
            #if open list but empty -> discard and create new list:
            elif num_prods == 0:
                db_interactor.delete_ordlist(conn, cursor, slots['ord_code'])
                slots['ord_code'] = db_interactor.get_new_ordlist(conn, cursor, supplier)
                message = f"Ti ho creato una nuova lista!"
                dispatcher.utter_message(text=message)
                slots['new_list'] = True

            #load open list:
            else:
                #prepare strings for message:
                num_str = f"{num_prods} prodotti"
                if num_prods == 1:
                    num_str = "un prodotto"
                read_date = commons.readable_date(slots['ord_date'])
                message = f"Abbiamo una lista aperta, modificata per ultimo {read_date}, con {num_str}."
                dispatcher.utter_message(text=message)
                slots['new_list'] = False

            conn.close()

        except:
            print("DB connection error.")
            message = "C'è stato un problema con il mio database, ti chiedo scusa."
            dispatcher.utter_message(text=message)
            slots['fail'] = True
        
        slots_set = commons.convert_to_slotset(slots)
        return slots_set


#Create Order -> create new order list into DB:
class ActionGetNewList(Action):
    def name(self) -> Text:
            return "action_get_newlist"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        #get slots saved:
        supplier = tracker.get_slot("supplier")
        slots = {}
        slots['ord_code'] = tracker.get_slot("ord_code")
        try:
            conn, cursor = db_connect()
            if slots['ord_code'] != None:
                db_interactor.delete_ordlist(conn, cursor, slots['ord_code'])
            slots['ord_code'] = db_interactor.get_new_ordlist(conn, cursor, supplier)
            message = f"Ti ho creato una nuova lista, useremo questa!"
            dispatcher.utter_message(text=message)
            conn.close()
        except:
            print("DB connection error.")
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
            slots['ord_list'], num_prods = db_interactor.get_suggestion_list(conn, slots['supplier'], slots['ord_code'])
            conn.close()
            #if extracted suggestion list empty:
            if slots['ord_list'] == None:
                slots['found'] = False
                message = f"Non ho trovato altri prodotti di {slots['supplier']} con meno di {THRESHOLD_TO_ORD} pezzi!"
                dispatcher.utter_message(text=message)
            #else: trigger start read:
            else:
                slots['found'] = True
                if num_prods == 1:
                    num_str = "un solo prodotto"
                    start_str = ""
                else:
                    num_str = f"{num_prods} prodotti"
                    start_str = " Inizio a leggere!"
                message = f"Ti ho trovato {num_str} di {slots['supplier']} con meno di {THRESHOLD_TO_ORD} pezzi.{start_str}"
                dispatcher.utter_message(text=message)
        except:
            print("DB connection error.")
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
        slots = commons.read_ord_list(dispatcher, ord_list)
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
        slots = commons.read_ord_list(dispatcher, slots['ord_list'], suggest_mode=True)
        if slots['p_code'] != None:
            dispatcher.utter_message(response='utter_ask_sugg_pieces')
        
        slots_set = commons.convert_to_slotset(slots)
        return slots_set


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


#Loopers -> Warehouse update:
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
        
        slots = commons.disambiguate_prod(tracker, dispatcher, pieces=True)
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
            slots = commons.update_warehouse(dispatcher, slots)
        else:
            message = f"Mmm, non ho capito il numero di pezzi."
            dispatcher.utter_message(text=message)
            slots['pieces'] = None
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
        slots['pieces'] = next(tracker.get_latest_entity_values("pieces"), None)

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
        print("Ok", slots['keep'], slots['pieces'])
        slots = commons.update_ord_list(dispatcher, slots)
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
        slots = commons.disambiguate_prod(tracker, dispatcher, supplier=supplier)
        return slots

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
            print("Ok", slots['p_code'], slots['pieces'])
            slots = commons.write_ord_list(dispatcher, slots, next_slot='p_code')
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
        slots['pieces'] = next(tracker.get_latest_entity_values("pieces"), None)

        #cases:
        #a) if no pieces given by user:
        if slots['pieces'] == None:
            #a.1) if intent is ignore product:
            if slots['add_sugg'] == False:
                dispatcher.utter_message(response='utter_skip')
                #update JSON reading list only (no DB):
                slots['ord_list'] = commons.update_reading_list(slots['ord_list'])
                #if empty list:
                if slots['ord_list'] == None:
                    message = f"Non ho trovato altri prodotti di {slots['supplier']} con meno di {THRESHOLD_TO_ORD} pezzi!"
                    dispatcher.utter_message(text=message)
                    next_slot = None
                else:
                    dispatcher.utter_message(response='utter_ask_next')
                    next_slot = 'add_sugg'
                #reset/deactivate form, keeping stored only the slots to be used forward:
                slots = commons.reset_and_goto(slots, req_slot=next_slot, del_slots=['p_code', 'p_name', 'pieces', 'add_sugg'])

            else:
                #a.2) not understood:
                message = f"Mmm, non ho capito bene."
                dispatcher.utter_message(text=message)
                slots['add_sugg'] = None
                slots['pieces'] = None
                return slots

        #b) update order list in DB, JSON reading list and reset form:
        else:
            print("Ok", slots['add_sugg'], slots['pieces'])
            slots = commons.write_ord_list(dispatcher, slots, next_slot='add_sugg', update_json=True)
        return slots
