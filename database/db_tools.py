from globals import *

#DB TOOLS (BASICS):
# - db_connect()
# - create_tables()
# - drop_all()
# - empty_table()
# - drop_table()


#open DB connection:
def db_connect():
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
    except psycopg2.Error as e:
        log.error(e)
    return conn, cursor


#create tables:
def create_tables(conn, cursor, schema):
    #dict of queries:
    queries = {
        'Utenti': f'''CREATE TABLE Utenti (
            ID SERIAL NOT NULL,
            ChatID VARCHAR(20) NOT NULL,
            NomeUtente TEXT NOT NULL,
            Autorizzazione VARCHAR(20) NOT NULL,
            PRIMARY KEY (ID)
            )''',

        'Produttori': f'''CREATE TABLE {schema}.Produttori (
            Produttore VARCHAR(50) NOT NULL,
            ScontoMedio SMALLINT NOT NULL DEFAULT 0,
            PRIMARY KEY (Produttore)
            )''',

        'Categorie': f'''CREATE TABLE {schema}.Categorie (
            Categoria VARCHAR(50) NOT NULL,
            Aliquota NUMERIC(3,1) NOT NULL DEFAULT 22,
            PRIMARY KEY (Categoria)
            )''',

        'Prodotti': f'''CREATE TABLE {schema}.Prodotti (
            CodiceProd BIGINT NOT NULL, 
            Produttore VARCHAR(50) NOT NULL,
            Nome TEXT NOT NULL, 
            Categoria VARCHAR(50) NOT NULL,
            Quantita SMALLINT NOT NULL DEFAULT 0,
            Prezzo NUMERIC(5,2) NOT NULL DEFAULT 0,
            DispMedico BOOLEAN NOT NULL DEFAULT FALSE,
            EtaMinima SMALLINT NOT NULL DEFAULT 18,
            Bio BOOLEAN NOT NULL DEFAULT FALSE,
            Vegano BOOLEAN NOT NULL DEFAULT FALSE,
            SenzaGlutine BOOLEAN NOT NULL DEFAULT FALSE,
            SenzaLattosio BOOLEAN NOT NULL DEFAULT FALSE,
            SenzaZucchero BOOLEAN NOT NULL DEFAULT FALSE,
            PRIMARY KEY (CodiceProd),
            FOREIGN KEY (Produttore) REFERENCES {schema}.Produttori (Produttore) ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY (Categoria) REFERENCES {schema}.Categorie (Categoria) ON DELETE CASCADE ON UPDATE CASCADE
            )''',
        
        'StoricoOrdini': f'''CREATE TABLE {schema}.StoricoOrdini (
            CodiceOrd BIGINT NOT NULL,
            Produttore VARCHAR(50) NOT NULL,
            Riferimento TEXT,
            DataModifica VARCHAR(10) NOT NULL,
            DataInoltro VARCHAR(10),
            DataRicezione VARCHAR(10),
            PRIMARY KEY (CodiceOrd)
            )''',
            
        'ListeOrdini': f'''CREATE TABLE {schema}.ListeOrdini (
            ID SERIAL NOT NULL,
            CodiceOrd BIGINT NOT NULL, 
            CodiceProd BIGINT NOT NULL,
            Quantita SMALLINT NOT NULL DEFAULT 1,
            PRIMARY KEY (ID),
            FOREIGN KEY (CodiceOrd) REFERENCES {schema}.StoricoOrdini (CodiceOrd) ON DELETE CASCADE ON UPDATE CASCADE
            )'''
    }

    #execute:
    #1) create schema:
    try:
        cursor.execute(f"CREATE SCHEMA {schema}")
        conn.commit()
        log.info(f"Created schema {schema}.")
    except psycopg2.Error as e:
        log.error(f"Unable to create schema {schema}. {e}")
        return -1

    for t in queries.keys():
        try:
            cursor.execute(queries[t])
            conn.commit()
            log.info(f"Created table {t}.")
        except psycopg2.Error as e:
            log.error(f"Unable to create table {t}. {e}")
    return 0


#drop all tables in the schema (in globals):
def drop_all(conn, cursor, schema):
    try:
        query = f"DROP SCHEMA {schema} CASCADE"
        cursor.execute(query)
        conn.commit()
        log.info(f"Dropped schema {schema}.")
        return 0
    except psycopg2.Error as e:
        log.error(f"Unable to drop schema {schema}.")
        return -1


#empty a specific table:
def empty_table(conn, cursor, tablename, schema=None):
    if schema:
        loc = f"{schema}."
    else:
        loc = ""
    try:
        query = f"DELETE FROM {loc}{tablename}"
        cursor.execute(query)
        conn.commit()
        log.info(f"Table {loc}{tablename} successfully reset.")
        return 0
    except psycopg2.Error as e:
        log.error(f"ERROR: unable to reset {loc}{tablename} table.")
        return -1

#drop a specific table:
def drop_table(conn, cursor, tablename, schema=None):
    if schema:
        loc = f"{schema}."
    else:
        loc = ""
    try:
        query = f"DROP TABLE {loc}{tablename}"
        cursor.execute(query)
        conn.commit()
        log.info(f"Dropped table {loc}{tablename}.")
        return 0
    except psycopg2.Error as e:
        log.error(f"Unable to drop table {loc}{tablename}.")
        return -1
