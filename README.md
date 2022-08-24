# HMD_Herbie
Repo for *Herbie*, my final project for the Human-Machine Dialogue course 2021-22 at University of Trento.

The demo videos can be found in this YouTube [playlist](https://youtube.com/playlist?list=PLGwHqTQjI-2jbNqkYMIFJd--Elyg_0yfa).

<img src="./report/Herbie_icon.png" alt="drawing" width="200"/>

---

## Software requirements
Herbie has been developed in an **[Ubuntu](https://ubuntu.com/) 20.04 LTS** environment.

She makes use of the following software:
* [python](https://www.python.org/downloads/) 3.8.10
* [rasa](https://rasa.com/) 3.0.8
* [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) 13.11
* [psycopg2-binary](https://pypi.org/project/psycopg2/) 2.9.3
* [pandas](https://pandas.pydata.org/) 1.3.4
* [fuzzywuzzy](https://pypi.org/project/fuzzywuzzy/) 0.18.0
* [xlsxwriter](https://xlsxwriter.readthedocs.io/) 3.0.3
* [openpyxl](https://pypi.org/project/openpyxl/) 3.0.9
* [pytz](https://pypi.org/project/pytz/) 2021.3

She makes also use of the following built-in Python libraries: *math, random, configparser, datetime, logging, json, os, time.*

Herbie is configured to connect with [Amazon Alexa](https://developer.amazon.com/it-IT/alexa/alexa-skills-kit) for voice interaction. In order to connect Rasa with Alexa, it is necessary to install [ngrok](https://ngrok.com/) 2.3.40.

---

## Repo structure
Herbie's repo is structured as follows:

```
HMD_Herbie
├── actions                                 #rasa custom actions
│   ├── data_cache                          #target directory for temporary files
│   │   └── setfolder.ini
│   ├── __init__.py
│   ├── actions.py                          #main actions file used by rasa
│   ├── commons.py                          #helper functions
│   ├── orders.py                           #helper functions
│   ├── products.py                         #helper functions
│   └── views.py                            #helper functions
├── data                                    #training data
│   ├── stories
│   │   ├── find_product.yml
│   │   ├── supplier_1_various.yml
│   │   ├── supplier_2_order.yml
│   │   └── warehouse.yml
│   ├── nlu.yml
│   └── rules.yml
├── database                                #DB interaction functions (note: DB creation & administration functions are in Herbie Telegram Bot's repo)
│   ├── __init__.py
│   ├── db_export.py
│   ├── db_interactor.py
│   └── db_tools.py
├── logs                                    #logging directory
│   ├── bot_events.log
│   ├── db_events.log
│   └── setfolder.ini
├── models
│   ├── 20220817-124059-main.tar.gz         #final model, trained using the chosen pipeline ("main" pipeline)
│   └── setfolder.ini
├── report
│   ├── 221723_Report_HMD_Herbie.pdf        #project report
|   └── Herbie_icon.png                     #Herbie icon
├── results                                 #results of intrinsic evaluation
│   ├── core                                #results of rasa test core
│   │   ├── failed_test_stories.yml
│   │   ├── stories_with_warnings.yml
│   │   ├── story_confusion_matrix.png
│   │   ├── story_report.json
│   │   ├── rasa_test_core.log              #shell output of rasa test core
│   │   └── shell_test_suppl_order_2.log    #sample proof that test conversations don't fail if custom actions are run (i.e. via rasa shell)
│   ├── nlu_main                            #results of rasa test nlu on the "main" pipeline
│   │   ├── intent_confusion_matrix.png
│   │   ├── intent_errors.json
│   │   ├── intent_histogram.png
│   │   ├── intent_report.json
│   │   ├── train_intent_confusion_matrix.png
│   │   ├── train_intent_errors.json
│   │   ├── train_intent_histogram.png
│   │   └── train_intent_report.json
│   ├── nlu_alternative                     #results of rasa test nlu on the "alternative" pipeline
│   │   ├── model                           #trained model and config file for the "alternative" pipeline
│   │   │   ├── 20220817-210921-alternative.tar.gz
│   │   │   └── config-alt.yml
│   │   ├── intent_confusion_matrix.png
│   │   ├── intent_errors.json
│   │   ├── intent_histogram.png
│   │   ├── intent_report.json
│   │   ├── train_intent_confusion_matrix.png
│   │   ├── train_intent_errors.json
│   │   ├── train_intent_histogram.png
│   │   └── train_intent_report.json
├── tests                                   #test data
|   ├── nlu_test.yml                        #test set for rasa test nlu
|   ├── test_product.yml                    #test stories
|   ├── test_suppl_order_1.yml              #test stories
|   ├── test_suppl_order_2.yml              #test stories
|   ├── test_warehouse_1.yml                #test stories
|   └── test_warehouse_2.yml                #test stories
├── __init__.py
├── .gitignore
├── alexa_connector.py                      #connector to Alexa
├── alexa_schema.json                       #Alexa Skill reference schema
├── config.yml                              #chosen rasa pipeline ("main")
├── credentials.yml
├── domain.yml                              #domain file
├── endpoints.yml
├── globals.py                              #key global parameters and imports
├── local_credentials.ini                   #needed file for the connection to the DB and to Herbie Telegram Bot (details below)
└── README.md
```

---

## Launch Herbie
Herbie must be launched using the following instructions.

### 1) Add local_credentials.ini (important)
Before running Herbie, the file *local_credentials.ini* you received from the admin must be added to the main directory of the repo.

### 2.a) Interact via shell
Interact with Herbie via shell is simple. Two separate bash terminal windows are needed:
* In the first terminal window, run ```rasa run actions``` to execute Rasa's action server.
* In the second window, run ```rasa shell```. When Herbie is fully loaded, just start communicating.

### 2.b) Interact via voice (Alexa)

To connect to Alexa, the target Alexa Skill must be set to use the **Italian** language and to use an **HTTPS service endpoint**, in which a webhook must be inserted. The webhook will have the following default structure:
```
https://<customaddress>.ngrok.io/webhooks/alexa_assistant/webhook
```
The "\<customaddress\>" must be replaced with the personal ngrok address:
* Open a bash terminal and run ```./ngrok http 5005``` in order to expose the localhost via web.
* Copy the web address in the "Forwarding" row (i.e. *a66e-37-181-40-204*) and save it in the webhook in the endpoint console.

Keep ngrok running. Then, open two additional terminal windows:
* In the first additional window, run ```rasa run actions``` to execute Rasa's action server.
* In the second additional window, run ```rasa run -m models --endpoints endpoints.yml```.

When Herbie is fully loaded, ask Alexa to open the skill using the following **wake up words**:
```
Alexa, apri assistente negozio.
```
Then, start communicating with Herbie.

---

## Additional use notes
### Stop commands
When using Herbie via Alexa, conversations and loops can be stopped through one of two intents: 
* ***Stop***: managed by Alexa, it terminates the entire Skill (i.e. “basta”, “stop”, “chiudi”);
* ***Completed***: managed by Rasa, it ends only the current loop or conversation, depending on the case (i.e. “ho completato”, “finito”, “fatto”).

If you are using Herbie via shell, only the ***completed*** intent is available.

In all cases, Herbie proactively guides the user on what to say time by time.

### Register to Herbie Telegram Bot first
Herbie Vocal Assistant is set to communicate with Herbie Telegram Bot ([link to repo](https://github.com/ftrono/Herbie_Tbot)), which is available 24h for messaging at https://t.me/herbie_tbot. 

Make sure you **register** to the Telegram bot in order to receive the Excel printable views when you ask them via voice or shell. To register, open the Telegram Bot and run the command:
```
/registrami
```
Then, insert the passcode ("OTP") you received from the admin.

