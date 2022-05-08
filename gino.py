from database.db_tools import db_connect, db_disconnect
import database.db_interactor as db_interactor
import database.db_export as db_export
import actions.views as views
import pandas as pd
from globals import *


conn, cursor = db_connect()
query = "DELETE FROM test.storicoordini WHERE CodiceOrd = 20220501133426"
cursor.execute(query)
conn.commit()
db_disconnect(conn, cursor)


