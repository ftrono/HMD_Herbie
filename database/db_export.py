from globals import *
from database.db_tools import db_connect, db_disconnect


#get chat IDs to send the views to:
def get_chat_IDs():
    ids = []
    try:
        conn, cursor = db_connect()
        query = f"SELECT DISTINCT chatid FROM utenti WHERE nomeschema = '{SCHEMA}'"
        FullList = pd.read_sql(query, conn)
        ids = FullList['chatid'].tolist()
        db_disconnect(conn, cursor)
    except psycopg2.Error as e:
        dlog.error(f"Unable to extract chatID list for schema: {SCHEMA}. {e}")
    return ids


#get Products view from DB:
def get_view_prodotti(supplier=None):
    suppstr = ""
    FullList = pd.DataFrame()
    try:
        conn, cursor = db_connect()
        if supplier:
            suppstr = f"WHERE prodotti.produttore = '{supplier}'"
        query = f"SELECT prodotti.*, produttori.scontomedio, categorie.aliquota FROM {SCHEMA}.prodotti INNER JOIN {SCHEMA}.produttori ON prodotti.produttore = produttori.produttore INNER JOIN {SCHEMA}.categorie ON prodotti.categoria = categorie.categoria {suppstr} ORDER BY prodotti.produttore, prodotti.categoria, prodotti.nome"
        FullList = pd.read_sql(query, conn)
        db_disconnect(conn, cursor)
    except psycopg2.Error as e:
        dlog.error(f"Unable to perform get view Prodotti for supplier: {supplier if supplier else 'all'}. {e}")
    return FullList


#get Order List view from DB:
def get_view_listaordine(codiceord):
    OrdList = pd.DataFrame()
    try:
        conn, cursor = db_connect()
        query = f"SELECT listeordini.codiceprod, prodotti.produttore, prodotti.nome, prodotti.categoria, listeordini.quantita, prodotti.prezzo, produttori.scontomedio, categorie.aliquota FROM {SCHEMA}.listeordini INNER JOIN {SCHEMA}.prodotti ON listeordini.codiceprod = prodotti.codiceprod INNER JOIN {SCHEMA}.produttori ON prodotti.produttore = produttori.produttore INNER JOIN {SCHEMA}.categorie ON prodotti.categoria = categorie.categoria WHERE listeordini.codiceord = {codiceord} ORDER BY prodotti.produttore, prodotti.categoria, prodotti.nome"
        OrdList = pd.read_sql(query, conn)
        db_disconnect(conn, cursor)
    except psycopg2.Error as e:
        dlog.error(f"Unable to perform get view Lista Ordine for codiceord: {codiceord}. {e}")
    return OrdList
