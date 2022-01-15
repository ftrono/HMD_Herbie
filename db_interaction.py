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
    resp = []
    buf = {}

    #composable query:
    if 'p_code' in utts.keys():
        comp_str = "CodiceProd = ?"
        params.append(utts['p_code'])

    elif 'p_name' in utts.keys():
        comp_str = "Nome LIKE ?"
        name = "%"+utts['p_name']+"%"
        params.append(name)

        #additional pieces:
        if 'supplier' in utts.keys():
            comp_str = comp_str + " AND Produttore = ?"
            params.append(utts['supplier'])

        if 'line' in utts.keys():
            comp_str = comp_str + " AND Linea = ?"
            params.append(utts['line'])

        if 'category' in utts.keys():
            comp_str = comp_str + " AND Categoria = ?"
            params.append(utts['category'])
    else:
        msg = 'noinfo'
        return msg

    #composed:
    query = "SELECT CodiceProd, Produttore, Linea, Nome, Categoria FROM Prodotti WHERE " + comp_str

    #extract info:
    print(params)
    Prodotti = pd.read_sql(query, conn, params=params)
    if Prodotti.empty == False:
        for ind in Prodotti.index:
            buf['p_code'] = Prodotti['CodiceProd'][ind]
            buf['supplier'] = Prodotti['Produttore'][ind]
            buf['line'] = Prodotti['Linea'][ind]
            buf['p_name'] = Prodotti['Nome'][ind]
            buf['category'] = Prodotti['Categoria'][ind]
            resp.append(buf)
            buf = {}

    return resp


#MAIN:
if __name__ == '__main__':
    conn, cursor = db_connect()
    utts = {'p_code': 12345, 'p_name': 'flufast', 'supplier': 'biosline', 'category': 'health', 'quantity': 2}
    add_prod(conn, cursor, utts)
    utts = {'p_code': 12346, 'p_name': 'pappa reale fiale', 'supplier': 'aboca', 'category': 'health', 'quantity': 3}
    add_prod(conn, cursor, utts)
    utts = {'p_code': 12347, 'p_name': 'pappa reale bustine', 'supplier': 'aboca', 'category': 'health', 'quantity': 5}
    add_prod(conn, cursor, utts)
    utts = {'p_name': 'pappa reale'}
    print(get_prodinfo(conn, utts))
    # utts = {'p_name': 'pappa reale fiale'}
    # delete_prod(conn, cursor, utts)
    conn.close()
