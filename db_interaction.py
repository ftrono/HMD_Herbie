from globals import *
from db_tools import db_connect

#DB_INTERACTIONS:
# - add_prod()
# - get_prodinfo()
# - get_quantity()
# - delete_prod()


#add a new product:
def add_prod(conn, cursor, utts):

    tup = (str(utts['idprod']), utts['nameprod'], utts['azienda'])
    try:
        cursor.execute("INSERT INTO Prodotti (IDProdotto, NomeProdotto, Azienda) VALUES (?, ?, ?)", tup)
        log.info("Added product {} to table Prodotti.".format(utts['nameprod']))
    except sqlite3.Error as e:
        log.error("Unable to add product {} to table Prodotti. {}".format(utts['nameprod'], e))

    tup = (str(utts['idprod']), utts['quantity'])
    try:
        cursor.execute("INSERT INTO Magazzino (IDProdotto, Quantità) VALUES (?, ?)", tup)
        log.info("Added product {} to table Magazzino.".format(utts['nameprod']))
    except sqlite3.Error as e:
        log.error("Unable to add product {} to table Magazzino. {}".format(utts['nameprod'], e))

    conn.commit()

    return 0


#delete a product:
def delete_prod(conn, cursor, utts):
    nameprod = utts['nameprod']
    try:
        cursor.execute("DELETE FROM Prodotti WHERE NomeProdotto = ?", [nameprod])
        log.info("Deleted product {} from DB.".format(utts['nameprod']))
    except sqlite3.Error as e:
        log.error("Unable to delete product {} from DB. {}".format(utts['nameprod'], e))

    conn.commit()


#get basic product info:
def get_prodinfo(conn, utts):
    #vars:
    params = [utts['nameprod']]

    #composable query:
    if 'description' in utts.keys():
        str_ds = " AND Descrizione = ?"
        params.append(utts['description'])
    else:
        str_ds = ""

    if 'azienda' in utts.keys():
        str_az = " AND Azienda = ?"
        params.append(utts['azienda'])
    else:
        str_az = ""

    #composed:
    query = "SELECT IDProdotto, NomeProdotto, Azienda FROM Prodotti WHERE NomeProdotto = ?"+str_ds+str_az

    #extract info:
    Prodotto = pd.read_sql(query, conn, params=params)
    idprod = str(Prodotto['IDProdotto'].iloc[0])
    azienda = Prodotto['Azienda'].iloc[0]

    return idprod, azienda


#MAIN:
if __name__ == '__main__':
    conn, cursor = db_connect()
    utts = {'idprod': 12345, 'nameprod': 'FluFast', 'azienda': 'BiosLine', 'quantity': 2}
    add_prod(conn, cursor, utts)
    nameprod = 'FluFast'
    print(get_prodinfo(conn, utts))
    #delete_prod(conn, cursor, utts)
    conn.close()
