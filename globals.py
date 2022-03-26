import sqlite3, logging, time, json, pytz
from datetime import datetime, date
import pandas as pd

#GLOBAL IMPORTS, PARAMETERS & INSTANTIATIONS:

#globals:
DB_FILE = "erb_copertino.db"
THRESHOLD_TO_ORD = 5
MONTHS = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]

#Set logger:
log=logging.getLogger('db_interactions')
hdl=logging.FileHandler('./logs/db_interactions.log',mode='a')
hdl.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
log.setLevel(logging.INFO)
log.addHandler(hdl)

