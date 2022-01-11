from globals import *

#DB TOOLS:
# - db_connect()
# - create_tables()
# - drop_all()
# - empty_table()


#open DB connection:
def db_connect():
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.execute("PRAGMA foreign_keys = 1")
        cursor = conn.cursor()
    except sqlite3.Error as e:
        log.error(e)
    return conn, cursor


#create tables:
def create_tables(conn=None, cursor=None):
    if not conn:
        connect = True
        conn, cursor = db_connect()
    else:
        connect = False

    #dict of queries:
    queries = {
        'Prodotti': '''CREATE TABLE Prodotti (
            IDProdotto TEXT PRIMARY KEY, 
            Azienda TEXT NOT NULL, 
            NomeProdotto TEXT NOT NULL, 
            Descrizione TEXT)''',
            
        'Magazzino': '''CREATE TABLE Magazzino (
            IDProdotto TEXT PRIMARY KEY, 
            Quantità INTEGER NOT NULL DEFAULT 0, 
            Scaffale INTEGER,
            FOREIGN KEY (IDProdotto) REFERENCES Prodotti (IDProdotto) ON DELETE CASCADE ON UPDATE CASCADE)'''
    }

    #execute:
    for t in queries.keys():
        try:
            cursor.execute(queries[t])
            conn.commit()
            log.info("Created table {}".format(t))
        except:
            log.error("Unable to create table " + t)
    
    if connect == True:
        conn.close()
    return 0


#drop all tables:
def drop_all(conn=True, cursor=True):
    if not conn:
        connect = True
        conn, cursor = db_connect()
    else:
        connect = False

    #ordered list of tables:
    tables = ['Magazzino', 'Prodotti']

    #execute:
    for t in tables:
        try:
            query = 'DROP TABLE '+ t
            cursor.execute(query)
            conn.commit()
            log.info("Dropped table {}".format(t))
        except:
            log.error("Unable to drop table "+t)

    if connect == True:
        conn.close()
    return 0


#empty a specific table:
def empty_table(tablename, conn=None, cursor=None):
    if not conn:
        connect = True
        conn, cursor = db_connect()
    else:
        connect = False
    
    try:
        query = "TRUNCATE TABLE "+tablename
        cursor.execute(query)
        conn.commit()
        log.info("Table "+tablename+" successfully reset.")
    except:
        log.error("ERROR: unable to reset "+tablename+" table.")
    
    if connect == True:
        conn.close()
    return 0


#MAIN:
if __name__ == '__main__':
    conn, cursor = db_connect()
    drop_all(conn, cursor)
    create_tables(conn, cursor)
    conn.close()
