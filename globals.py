import sqlite3, logging, time
import pandas as pd

#globals:
DB_FILE = "erb_copertino.db"

#Set logger:
log=logging.getLogger('db_interactions')
hdl=logging.FileHandler('./logs/db_interactions.log',mode='a')
hdl.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
log.setLevel(logging.INFO)
log.addHandler(hdl)

