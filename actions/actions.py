from typing import Any, Text, Dict, List
from rasa_sdk import Tracker, Action, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from globals import *
from db_tools import db_connect
from db_interaction import get_prodinfo

#HELPER:
#get product reference from DB:
def get_p_code(tracker, dispatcher, p_text):
   
    utts = {
        'p_code': next(tracker.get_latest_entity_values("p_code"), None), 
        'p_text': str(p_text).lower()
        }

    #fallback:
    if utts['p_code'] == None and utts['p_text'] == None:
        message = f"Mmm, mi manca qualche informazione."
        message = "Puoi leggermi il codice a barre, oppure dirmi il nome del prodotto e il produttore!"
        dispatcher.utter_message(text=message)
        return None

    elif utts['p_code'] != None:
        #p_code has priority:
        utts['p_code'] = str(utts['p_code']).lower()
    
    #db extraction:
    try:
        conn, cursor = db_connect()   
        resp = get_prodinfo(conn, utts)
        conn.close()
    except:
        resp == []
    
    #fallback: not found:
    if resp == []:
        if utts['p_code'] != None:
            str1 = "codice"
        else:
            str1 = "nome"
        message = f"Non ho trovato nessun prodotto con questo " + str1 + ". Riproviamo!"
        dispatcher.utter_message(text=message)
        return None

    elif len(resp) > 1:
        message = f"Ho trovato più di un prodotto simile:"
        for prod in resp:
            message = message + "\nDi " + prod['supplier'] + ", " + prod['p_name'] + "."
        message = message + "\nProva a specificare meglio!"
        dispatcher.utter_message(text=message)
        return None

    else:
        prod = resp[0]
        message = f"Trovato! Di {prod['supplier']}, {prod['p_name']}."
        dispatcher.utter_message(text=message)
        return prod


#CUSTOM ACTIONS:
class ValidateMagazzinoForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_magazzino_form"

    def validate_p_text(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:

        p_text = tracker.latest_message.get("text")
        print(p_text)
        prod = get_p_code(tracker, dispatcher, p_text)
        if prod is None:
            slots = {"p_text": None}
        else:
            slots = {"p_text": 'ok', "p_code": str(prod['p_code']), "p_name": str(prod['p_name']), "supplier": str(prod['supplier'])}
        return slots


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

