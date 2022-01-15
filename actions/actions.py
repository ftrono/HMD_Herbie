# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from globals import *
from db_tools import db_connect
from db_interaction import get_prodinfo
#import arrow ?


class GetProd(Action):
    def name(self) -> Text:
        return "action_getprod"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        utts = {}
        #get latest entity values from tracker, or None if they're not available:
        p_code = next(tracker.get_latest_entity_values("p_code"), None)
        p_name = next(tracker.get_latest_entity_values("p_name"), None)
        supplier = next(tracker.get_latest_entity_values("supplier"), None)

        #fallback: under informative:
        # - case a) no info
        # - case b) p_code (it's self-sufficient)
        # - case c) p_name + supplier
        if p_name == None and p_code == None:
            message = f"Mmm, mi manca qualche informazione."
            dispatcher.utter_message(response="utter_need_prodid")
            return []
        elif p_code != None:
            utts['p_code'] = p_code.lower()
        else:
            utts['p_name'] = p_name.lower()
            if supplier != None:
                utts['supplier'] = supplier.lower()
        
        #db extraction:
        try:
            conn, cursor = db_connect()   
            resp = get_prodinfo(conn, utts)
            conn.close()
        except:
            resp == []
        
        #fallback: not found:
        if resp == []:
            if p_code != None:
                message = f"Non ho trovato nessun prodotto con questo codice. Riproviamo!"
            else:
                message = f"Non ho trovato nessun prodotto con questo nome. Riproviamo!"
            dispatcher.utter_message(text=message)
            dispatcher.utter_message(response="utter_need_prodid")
            return []
        elif len(resp) > 1:
            message = f"Ho trovato più di un prodotto simile:"
            for prod in resp:
                message = message + "\nDi " + prod['supplier'] + ", " + prod['p_name'] + "."
            message = message + "\n Prova a specificare meglio!"
            dispatcher.utter_message(text=message)
            dispatcher.utter_message(response="utter_need_prodid")
            return []
        else:
            prod = resp[0]
            message = f"Trovato! Di {prod['supplier']}, {prod['p_name']}."
            dispatcher.utter_message(text=message)
            return[SlotSet("p_code", str(prod['p_code']))]


class GetAzienda(Action):
    def name(self) -> Text:
        return "action_get_azienda"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        utts = {}
        nomatch = False
        #get latest entity value from tracker, or None if it's not available:
        p_name = next(tracker.get_latest_entity_values("p_name"), None)

        #fallback: under informative:
        if not p_name:
            #utter: return a generally applicable message
            message = f"Mmm, non ho capito il nome del prodotto."
            dispatcher.utter_message(text=message)
            return []
        else:
            utts['p_name'] = p_name.lower()
        
        #db extraction:
        try:
            conn, cursor = db_connect()   
            resp = get_prodinfo(conn, utts)
            conn.close()
            print(resp)
            if resp == {}:
                nomatch = True
        except:
            nomatch = True
        
        #fallback: not found:
        if nomatch == True:
            #utter: no match
            message = f"Non ho trovato nessun prodotto chiamato {p_name}. Prova a rilanciare!"
            dispatcher.utter_message(text=message)
            return []
        else:
            message = f"{p_name} è un prodotto di {resp['supplier']}."
            dispatcher.utter_message(text=message)
            return []
            #or:
            #return[SlotSet("location", cur_entity)] #if wanting to set the save the variable for the future knowledge

