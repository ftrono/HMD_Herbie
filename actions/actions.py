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
#import arrow ?


class ActionHelloWorld(Action):

    def name(self) -> Text:
        return "action_hello_world"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        #get latest entity value from tracker, or None if it's not available:
        cur_entity = next(tracker.get_latest_entity_values("place"), None)

        #fallback: under informative:
        if not cur_entity:
            #utter: return a generally applicable message
            message = "Sorry, I did not get that."
            dispatcher.utter_message(text=message)
            return []

        #custom code here

        #(db etraction:)
        result = 0
        #result = db.get(cur_entity, None)
        if not result:
            #utter:
            message = "Sorry, I did not find {cur_entity} in my database."
            dispatcher.utter_message(text=message)
            return []

        #utter:
        message = "Hello World!"
        dispatcher.utter_message(text=message)
        return []
        #or:
        #return[SlotSet("location", cur_entity)] #if wanting to set the save the variable for the future knowledge
