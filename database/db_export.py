from globals import *
from database.db_tools import db_connect, db_disconnect


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

#get Recap view from DB:
def get_view_recap():
    Recap = pd.DataFrame()
    try:
        conn, cursor = db_connect()
        query = f"SELECT produttori.produttore, categorie.categoria, SUM(prodotti.quantita) AS quantita, SUM(prodotti.valoretotale) AS valoretotale, produttori.scontomedio, categorie.aliquota FROM {SCHEMA}.produttori INNER JOIN {SCHEMA}.prodotti ON prodotti.produttore = produttori.produttore INNER JOIN {SCHEMA}.categorie ON prodotti.categoria = categorie.categoria GROUP BY produttori.produttore, categorie.categoria ORDER BY produttori.produttore, categorie.categoria"
        Recap = pd.read_sql(query, conn)
        db_disconnect(conn, cursor)
    except psycopg2.Error as e:
        dlog.error(f"Unable to perform get view Recap from schema {SCHEMA}. {e}")
    return Recap

#get Storico Ordini view from DB:
def get_view_storicoordini():
    History = pd.DataFrame()
    try:
        conn, cursor = db_connect()
        query = f"SELECT * FROM {SCHEMA}.storicoordini ORDER BY datamodifica DESC"
        History = pd.read_sql(query, conn)
        db_disconnect(conn, cursor)
    except psycopg2.Error as e:
        dlog.error(f"Unable to perform get view Storico Ordini from schema {SCHEMA}. {e}")
    return History

#get Order List view from DB:
def get_view_listaordine(supplier=None, codiceord=None):
    OrdList = pd.DataFrame()
    try:
        conn, cursor = db_connect()
        filterstr= f"WHERE listeordini.codiceord = {codiceord}" if codiceord else f"WHERE prodotti.produttore = '{supplier}'"
        query = f"SELECT listeordini.codiceprod, prodotti.produttore, prodotti.nome, prodotti.categoria, listeordini.quantita, prodotti.prezzo, produttori.scontomedio, categorie.aliquota FROM {SCHEMA}.listeordini INNER JOIN {SCHEMA}.prodotti ON listeordini.codiceprod = prodotti.codiceprod INNER JOIN {SCHEMA}.produttori ON prodotti.produttore = produttori.produttore INNER JOIN {SCHEMA}.categorie ON prodotti.categoria = categorie.categoria {filterstr} ORDER BY prodotti.produttore, prodotti.categoria, prodotti.nome"
        OrdList = pd.read_sql(query, conn)
        db_disconnect(conn, cursor)
    except psycopg2.Error as e:
        dlog.error(f"Unable to perform get view Lista Ordine for supplier: {supplier if supplier else 'all'}. {e}")
    return OrdList

