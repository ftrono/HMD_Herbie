from pdb import Restart
from typing import Any, Text, Dict, List
from rasa_sdk import Tracker, Action, Action, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from rasa_sdk.events import AllSlotsReset, FollowupAction, SlotSet
from globals import *
from db_tools import db_connect
from db_interaction import get_prodinfo, check_quantity, update_quantity
    
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

        print("FORM RESTART TRIGGERED.")
        more = tracker.get_slot("more")
        if more == True:
            print("TRUE - Restarting")
            return [AllSlotsReset(), FollowupAction(name="magazzino_form")]
        elif more == False:
            print("FALSE - Resetting")
            return [AllSlotsReset()]
        else:
            print("NONE")
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

    def validate_quantity(
        self, 
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> Dict[Text, Any]:

        utts = {'p_code': None, 'value': None, 'oper': None}

        #validate user intent:
        intent = tracker.latest_message['intent'].get('name')
        print(tracker.latest_message['intent'].get('name'))
        if intent == 'inform_add_pieces':
            utts['oper'] = 'add'
        elif intent == 'inform_decr_pieces':
            utts['oper'] = 'decrease'
        else:
            message = "Mmm, non ho capito bene."
            dispatcher.utter_message(text=message)
            return {"quantity": None, "pieces": None}

        #get slots saved:
        slots = tracker.current_slot_values()
        print(slots['p_code'], slots['p_name'], slots['supplier'])

        #validate extracted no of pieces:
        utts['p_code'] = slots['p_code']
        utts['value'] = next(tracker.get_latest_entity_values("pieces"), None)

        #db extraction:
        if is_int(utts['value']) and int(utts['value']) > 0:
            print("Ok", utts['oper'], utts['value'])
            try:
                conn, cursor = db_connect()
                #check lower boundary:
                if utts['oper'] == 'decrease':
                    floor = check_quantity(cursor, utts)
                    if floor == 0:
                        message = f"La tua scorta era a zero, non ho potuto fare nulla. Riprova con un altro prodotto!"
                        dispatcher.utter_message(text=message)
                        return {"quantity": utts['oper'], "pieces": utts['value']}
                    if floor < utts['value']:
                        message = f"Ho trovato {floor} prodotti invece di {utts['value']}"
                        dispatcher.utter_message(text=message)
                        utts['value'] = floor
                #update DB:
                ret = update_quantity(conn, cursor, utts)

                conn.close()
            except:
                ret = -1
                print("DB connection error")

            if ret == 0 and utts['oper'] == 'add':
                message = f"Aggiunti {utts['value']} pezzi a {slots['p_name']} di {slots['supplier']}."
            elif ret == 0 and utts['oper'] == 'decrease':
                message = f"Ti ho rimossi {utts['value']} pezzi a {slots['p_name']} di {slots['supplier']}."
            else:
                message = "C'è stato un problema con il mio database, ti chiedo scusa. Riprova al prossimo turno!"
            dispatcher.utter_message(text=message)
            return {"quantity": utts['oper'], "pieces": utts['value']}
        else:
            print(utts['oper'], utts['value'])
            message = f"Mmm, non ho capito il numero di pezzi."
            dispatcher.utter_message(text=message)
            return {"quantity": None, "pieces": None}

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
            #reset all slots:
            # slots = tracker.current_slot_values()
            # for key in slots.keys():
            #     slots[key] = None
            print("Affermativo")
            return {"more": True}

        elif intent == 'deny':
            print("Negativo")
            message = f"Ok! Se ti serve altro mi trovi qui quando vuoi!"
            dispatcher.utter_message(text=message)
            return {"more": False}

        else:
            message = "Mmm, non ho capito bene."
            dispatcher.utter_message(text=message)
            return {"more": None}


