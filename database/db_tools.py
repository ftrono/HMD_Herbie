from globals import *

#DB TOOLS:
# - db_connect()
# - db_disconnect()

#open DB connection:
def db_connect():
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
    except psycopg2.Error as e:
        log.error(e)
    return conn, cursor

#close DB connection:
def db_disconnect(conn, cursor):
    try:
        cursor.close()
        conn.close()
    except psycopg2.Error as e:
        log.error(e)
