import sqlite3, logging, time, json
import pandas as pd

#globals:
DB_FILE = "erb_copertino.db"
THRESHOLD_TO_ORD = 10
MONTHS = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]

#Set logger:
log=logging.getLogger('db_interactions')
hdl=logging.FileHandler('./logs/db_interactions.log',mode='a')
hdl.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
log.setLevel(logging.INFO)
log.addHandler(hdl)

