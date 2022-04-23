import os, psycopg2, logging, configparser, time, json, pytz
from datetime import datetime, date
import pandas as pd
import telegram

#GLOBAL IMPORTS, PARAMETERS & INSTANTIATIONS:

#GLOBALS:
THRESHOLD_TO_ORD = 5
MONTHS = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]

#Config:
#DB:
config = configparser.ConfigParser()
config.read(os.getcwd()+"/database/db_credentials.ini")
d_conf = config['DB']
DATABASE_URL = d_conf.get('database_url')
SCHEMA = d_conf.get('schema')

#t-Bot (for sending messages):
config.read(os.getcwd()+"/t_credentials.ini")
t_conf = config['TELEGRAM']
TOKEN = t_conf.get('token')
TBOT = telegram.Bot(token=TOKEN)

#LOGS:
#db log:
dlog=logging.getLogger('db_events')
hdl=logging.FileHandler('./logs/db_events.log',mode='a')
hdl.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
dlog.setLevel(logging.INFO)
dlog.addHandler(hdl)

#events log:
elog=logging.getLogger('bot_events')
hdl=logging.FileHandler('./logs/bot_events.log',mode='a')
hdl.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
elog.setLevel(logging.INFO)
elog.addHandler(hdl)
