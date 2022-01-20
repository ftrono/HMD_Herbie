from pdb import Restart
from typing import Any, Text, Dict, List
from rasa_sdk import Tracker, Action, Action, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from rasa_sdk.events import AllSlotsReset, FollowupAction, SlotSet
from globals import *
from db_tools import db_connect
from db_interaction import get_prodinfo, check_pieces, update_pieces
    
#HELPER:
#Get product reference from DB:
def get_p_code(tracker, dispatcher, p_text):
    utts = {
        'p_code': next(tracker.get_latest_entity_values("p_code"), None), 
        'p_text': str(p_text).lower()
        }

    #fallback:
    if utts['p_code'] == None and utts['p_text'] == None:
        message = f"Mmm, mi manca qualche informazione."
        #message = "Puoi leggermi il codice a barre, oppure dirmi il nome del prodotto e il produttore!"
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
        resp = []
    
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


#Check if a string is an integer:
def is_int(string: Text) -> bool:
    try:
        int(string)
        return True
    except ValueError:
        return False


class ActionRestartMagazzinoForm(Action):
    def name(self) -> Text:
            return "action_restart_magazzino_form"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:

        more = tracker.get_slot("more")

        if more == True:
            return [AllSlotsReset(), FollowupAction(name="magazzino_form")]
        elif more == False:
            return [AllSlotsReset()]
        else:
            return []

#Forms validation:
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

    def validate_variation(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> Dict[Text, Any]:

        utts = {'p_code': None, 'pieces': None, 'var': None}

        #validate user intent:
        intent = tracker.latest_message['intent'].get('name')
        print(tracker.latest_message['intent'].get('name'))
        if intent == 'inform_add_pieces':
            utts['var'] = 'add'
        elif intent == 'inform_decr_pieces':
            utts['var'] = 'decrease'
        else:
            message = "Mmm, non ho capito bene."
            dispatcher.utter_message(text=message)
            return {"variation": None, "pieces": None}

        #get slots saved:
        slots = tracker.current_slot_values()
        print(slots['p_code'], slots['p_name'], slots['supplier'])

        #validate extracted no of pieces:
        utts['p_code'] = slots['p_code']
        utts['pieces'] = next(tracker.get_latest_entity_values("pieces"), None)

        #db extraction:
        if is_int(utts['pieces']) and int(utts['pieces']) > 0:
            print("Ok", utts['var'], utts['pieces'])
            try:
                conn, cursor = db_connect()
                #check lower boundary:
                if utts['var'] == 'decrease':
                    floor = check_pieces(cursor, utts)

                    if floor == 0:
                        message = f"La tua scorta era a zero, non ho potuto fare nulla. Riprova con un altro prodotto!"
                        dispatcher.utter_message(text=message)
                        return {"variation": utts['var'], "pieces": utts['pieces']}

                    if floor < int(utts['pieces']):
                        if floor == 1:
                            str1 = "un pezzo"
                        else:
                            str1 = f"{floor} pezzi"
                        message = "Ho trovato solo " + str1 + "."
                        dispatcher.utter_message(text=message)
                        utts['pieces'] = floor

                #update DB:
                ret = update_pieces(conn, cursor, utts)
                conn.close()
            except:
                ret = -1
                print("DB connection error")
            
            if int(utts['pieces']) == 1:
                str1 = "un pezzo"
            else:
                str1 = f"{utts['pieces']} pezzi"

            if ret == 0 and utts['var'] == 'add':
                message = f"Ti ho aggiunto {str1} a {slots['p_name']} di {slots['supplier']}."
            elif ret == 0 and utts['var'] == 'decrease':
                message = f"Ti ho rimosso {str1} a {slots['p_name']} di {slots['supplier']}."
            else:
                message = "C'è stato un problema con il mio database, ti chiedo scusa. Riprova al prossimo turno!"
            dispatcher.utter_message(text=message)
            return {"variation": utts['var'], "pieces": utts['pieces']}
        else:
            print(utts['var'], utts['pieces'])
            message = f"Mmm, non ho capito il numero di pezzi."
            dispatcher.utter_message(text=message)
            return {"variation": None, "pieces": None}

    def validate_more(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> Dict[Text, Any]:

        #validate user intent:
        intent = tracker.latest_message['intent'].get('name')

        if intent == 'affirm':
            print("Affermativo")
            return {"more": True}

        elif intent == 'deny':
            print("Negativo")
            dispatcher.utter_message(response="utter_ok")
            dispatcher.utter_message(response="utter_available")
            return {"more": False}

        else:
            message = "Mmm, non ho capito bene."
            dispatcher.utter_message(text=message)
            return {"more": None}


