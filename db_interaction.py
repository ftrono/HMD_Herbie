from globals import *
from db_tools import db_connect

#DB_INTERACTIONS:
# - add_prod()
# - get_prodinfo()
# - get_quantity()
# - delete_prod()


#add a new product:
def add_prod(conn, cursor, utts):

    tup = (str(utts['p_code']), utts['supplier'], utts['p_name'], utts['category'])
    try:
        cursor.execute("INSERT INTO Prodotti (CodiceProd, Produttore, Nome, Categoria) VALUES (?, ?, ?, ?)", tup)
        log.info("Added product {} to table Prodotti.".format(utts['p_name']))
    except sqlite3.Error as e:
        log.error("Unable to add product {} to table Prodotti. {}".format(utts['p_name'], e))

    # tup = (str(utts['p_code']), utts['quantity'])
    # try:
    #     cursor.execute("INSERT INTO Magazzino (CodiceProd, Quantità) VALUES (?, ?)", tup)
    #     log.info("Added product {} to table Magazzino.".format(utts['p_name']))
    # except sqlite3.Error as e:
    #     log.error("Unable to add product {} to table Magazzino. {}".format(utts['p_name'], e))

    conn.commit()

    return 0


#delete a product:
def delete_prod(conn, cursor, utts):
    p_name = utts['p_name']
    try:
        cursor.execute("DELETE FROM Prodotti WHERE Nome = ?", [p_name])
        log.info("Deleted product {} from DB.".format(utts['p_name']))
    except sqlite3.Error as e:
        log.error("Unable to delete product {} from DB. {}".format(utts['p_name'], e))

    conn.commit()


#get basic product info:
def get_prodinfo(conn, utts):
    #vars:
    params = []
    resp = {}

    #composable query:
    if 'p_code' in utts.keys():
        str_init = "CodiceProd = ?"
        params.append(utts['p_code'])

    elif 'p_name' in utts.keys():
        str_init = "Nome = ?"
        params.append(utts['p_name'])

        #additional pieces:
        if 'descr' in utts.keys():
            str_ds = " AND Descrizione = ?"
            params.append(utts['descr'])
        else:
            str_ds = ""

        if 'supplier' in utts.keys():
            str_az = " AND Produttore = ?"
            params.append(utts['supplier'])
        else:
            str_az = ""

        if 'line' in utts.keys():
            str_ln = " AND Linea = ?"
            params.append(utts['line'])
        else:
            str_ln = ""

        if 'category' in utts.keys():
            str_ct = " AND Categoria = ?"
            params.append(utts['category'])
        else:
            str_ct = ""
    else:
        msg = 'noinfo'
        return msg

    #composed:
    query = "SELECT CodiceProd, Produttore, Linea, Nome, Descrizione, Categoria FROM Prodotti WHERE " + str_init + str_ds + str_az + str_ln + str_ct

    #extract info:
    print(params)
    Prodotto = pd.read_sql(query, conn, params=params)
    if Prodotto.empty == False:
        resp['p_code'] = Prodotto['CodiceProd'].iloc[0]
        resp['supplier'] = Prodotto['Produttore'].iloc[0]
        resp['line'] = Prodotto['Linea'].iloc[0]
        resp['p_name'] = Prodotto['Nome'].iloc[0]
        resp['descr'] = Prodotto['Descrizione'].iloc[0]
        resp['category'] = Prodotto['Categoria'].iloc[0]

    return resp


#MAIN:
if __name__ == '__main__':
    conn, cursor = db_connect()
    utts = {'p_code': 12345, 'p_name': 'flufast', 'supplier': 'biosline', 'category': 'health', 'quantity': 2}
    add_prod(conn, cursor, utts)
    utts = {'p_code': 12346, 'p_name': 'pappa reale', 'supplier': 'aboca', 'category': 'health', 'quantity': 3}
    add_prod(conn, cursor, utts)
    utts = {'p_name': 'pappa reale'}
    print(get_prodinfo(conn, utts))
    #delete_prod(conn, cursor, utts)
    conn.close()
