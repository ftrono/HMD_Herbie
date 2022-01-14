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


class GetAzienda(Action):

    def name(self) -> Text:
        return "action_get_azienda"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        #vars:
        utts = {}
        nomatch = False

        #get latest entity value from tracker, or None if it's not available:
        nameprod = next(tracker.get_latest_entity_values("nameprod"), None)

        #fallback: under informative:
        if not nameprod:
            #utter: return a generally applicable message
            message = f"Mmm, non ho capito il nome del prodotto."
            dispatcher.utter_message(text=message)
            return []
        else:
            utts['p_name'] = nameprod.lower()

        #db extraction:
        conn, cursor = db_connect()        

        try:
            resp = get_prodinfo(conn, utts)
            print(resp)
            if resp == {}:
                nomatch = True
        except:
            nomatch = True
        
        #fallback: not found:
        if nomatch == True:
            #utter: no match
            message = f"Non ho trovato nessun prodotto chiamato {nameprod}. Prova a rilanciare!"
            dispatcher.utter_message(text=message)
            return []

        #utter:
        message = f"{nameprod} è un prodotto di {resp['supplier']}."
        dispatcher.utter_message(text=message)
        conn.close()
        return []
        #or:
        #return[SlotSet("location", cur_entity)] #if wanting to set the save the variable for the future knowledge
