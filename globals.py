import os, psycopg2, logging, configparser, time, json, pytz
from datetime import datetime, date
import pandas as pd

#GLOBAL IMPORTS, PARAMETERS & INSTANTIATIONS:

#GLOBALS:
THRESHOLD_TO_ORD = 5
MONTHS = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]

#Config:
config = configparser.ConfigParser()
print(os.getcwd())
config.read(os.getcwd()+"/database/db_credentials.ini")
t_conf = config['DB']
DATABASE_URL = t_conf.get('database_url')
SCHEMA = t_conf.get('schema')

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
