from datetime import datetime
import pytz
from globals import *
from db_tools import db_connect

#DB_INTERACTIONS

#get basic product info:
def get_prodinfo(conn, utts):
    #vars:
    params = []
    resp = []
    buf = {}
    to_pop = []

    #if p_code is available:
    if utts['p_code'] != None:
        print(utts['p_code'])
        try:
            #directly extract the matching product (direct match):
            query = "SELECT CodiceProd, Produttore, Nome, Categoria FROM Prodotti WHERE CodiceProd = ?"
            params = [str(utts['p_code'])]
            Prodotti = pd.read_sql(query, conn, params=params)
        except sqlite3.Error as e:
            log.error(f"DB query error for 'p_code'. {e}")

    else:
        #tokenize p_text to extract p_name:
        p_text = utts['p_text'].strip()
        tokens = p_text.split()
        print(tokens)

        if utts['supplier'] == None:
            #get list of suppliers:
            suppl_tok = ''
            try:
                query = "SELECT DISTINCT Produttore FROM Prodotti"
                Suppliers = pd.read_sql(query, conn)
            except sqlite3.Error as e:
                log.error(f"DB query error for 'supplier'. {e}")
        else:
            suppl_tok = utts['supplier']

        #CASES:
        #1) find the first token for the supplier (if any) and remove it from tokens list:
        for token in tokens:
            Suppl = Suppliers[Suppliers['Produttore'].str.contains(token, na=False)]
            if Suppl.empty == False:
                #store token:
                suppl_tok = token
                to_pop.append(tokens.index(token))
                break
        
        #reduce tokens list:
        if to_pop != []:
            for item in reversed(to_pop):
                tokens.pop(item)
            to_pop = []
        
        #FALLBACK: if only supplier given:
        if len(tokens) == 0:
            return []

        #prepare p_name query:
        sel1 = "Nome LIKE ?"
        sel2 = ""
        if suppl_tok != '':
            sel2 = " AND Produttore LIKE ?"
        
        #2) query DB for p_name (get first series of matches) and reduce residual tokens list:
        for token in tokens:
            try:
                #filter by p_name only or also by supplier:
                name = "%"+str(token)+"%"
                if suppl_tok != '':
                    params = [name, suppl_tok]
                else:
                    params = [name]
                #DB extract:
                query = "SELECT CodiceProd, Produttore, Nome, Categoria FROM Prodotti WHERE " + sel1 + sel2
                Prodotti = pd.read_sql(query, conn, params=params)
                to_pop.append(tokens.index(token))
                #if matches found:
                if Prodotti.empty == False:
                    break
            except sqlite3.Error as e:
                log.error(f"DB query error for p_name. {e}")

        #reduce tokens list:
        if to_pop != []:
            for item in reversed(to_pop):
                tokens.pop(item)
            to_pop = []

        #3) if first matching word found, progressively refine search in Pandas (word by word):
        if Prodotti.empty == False and len(tokens) != 0:
            #refine extraction:
            for token in tokens:
                Extr = Prodotti[Prodotti['Nome'].str.contains(token, na=False)]
                #replace with refined table:
                if Extr.empty == False:
                    Prodotti = Extr
        
    #COMMON: extract needed prod info to return:
    if Prodotti.empty == False:
        for ind in Prodotti.index:
            buf['p_code'] = Prodotti['CodiceProd'][ind]
            buf['supplier'] = Prodotti['Produttore'][ind]
            buf['p_name'] = Prodotti['Nome'][ind]
            buf['category'] = Prodotti['Categoria'][ind]
            resp.append(buf)
            buf = {}

    return resp


#look for supplier:
def get_supplier(conn, s_text):
    #vars:
    resp = []
    to_pop = []

    #tokenize p_text to extract supplier:
    s_text = s_text.strip()
    tokens = s_text.split()
    print(tokens)

    #get full list of suppliers from DB:
    try:
        query = "SELECT DISTINCT Produttore FROM Prodotti"
        Suppliers = pd.read_sql(query, conn)
    except sqlite3.Error as e:
        log.error(f"DB query error for 'supplier'. {e}")

    #CASES:
    #1) query DB for supplier (get first series of matches) and reduce residual tokens list:
    for token in tokens:
        Suppl = Suppliers[Suppliers['Produttore'].str.contains(token, na=False)]
        to_pop.append(tokens.index(token))
        if Suppl.empty == False:
            break

    #reduce tokens list:
    if to_pop != []:
        for item in reversed(to_pop):
            tokens.pop(item)
        to_pop = []
    
    #2) if first matching word found, progressively refine search in Pandas (word by word):
    if Suppl.empty == False and len(tokens) != 0:
        #refine extraction:
        for token in tokens:
            Extr = Suppl[Suppl['Produttore'].str.contains(token, na=False)]
            #replace with refined table:
            if Extr.empty == False:
                Suppl = Extr
        
    #3) extract full matching supplier name(s) to return:
    if Suppl.empty == False:
        for ind in Suppl.index:
            resp.append(str(Suppl['Produttore'][ind]))

    return resp


def get_pieces(cursor, p_code):
    #check products already in DB:
        query = f"SELECT Quantità FROM Prodotti WHERE CodiceProd = {p_code}"
        try:
            cursor.execute(query)
            quant = int(cursor.fetchall()[0][0])
            return quant
                        
        except sqlite3.Error as e:
            log.error(f"Unable to check quantity boundary for product code {p_code}. {e}")
            return -1


def update_pieces(conn, cursor, utts):
    #compose query:
    if utts['var'] == 'add':
        str1 = "+ " + str(utts['pieces'])
    elif utts['var'] == 'decrease':
        str1 = "- " + str(utts['pieces'])
    else:
        return -1
    query = "UPDATE Prodotti SET Quantità = Quantità " + str1 + " WHERE CodiceProd = " + str(utts['p_code'])

    #DB update:
    try: 
        cursor.execute(query)
        changes = cursor.rowcount
        if changes != 0:
            conn.commit()
            log.info(f"Success: {utts['var']} {utts['pieces']} pieces to product code {utts['p_code']}.")
            return 0
        else:
            log.error(f"DB: No match for p_code {utts['p_code']}.")
            return -1
    except sqlite3.Error as e:
        log.error(f"Unable to perform operation {utts['var']} to product code {utts['p_code']}. {e}")
        return -1


#delete an existent ord_list:
def delete_ordlist(conn, cursor, ord_code):
    try:
        query = f"DELETE FROM ListeOrdini WHERE CodiceOrd = {ord_code}"
        cursor.execute(query)
        query = f"DELETE FROM StoricoOrdini WHERE CodiceOrd = {ord_code}"
        cursor.execute(query)
        conn.commit()
        log.info(f"Success: deleted ord_list code {ord_code} from both tables ListeOrdini and StoricoOrdini.")
    except sqlite3.Error as e:
        log.error(f"Unable to delete ord_list code {ord_code}. {e}")
    return 0


#a) extract from DB latest open order list for the current supplier (if any):
def get_existing_ordlist(conn, supplier):
    latest_code = None
    latest_date = None
    full_list = None
    num_prods = 0
    try:
        query = f"SELECT CodiceOrd, DataModifica FROM StoricoOrdini WHERE Produttore = '{supplier}' AND DataInoltro IS NULL ORDER BY DataModifica DESC LIMIT 1"
        Latest = pd.read_sql(query, conn)
        if Latest.empty == False:
            #extract references:
            latest_code = int(Latest['CodiceOrd'].iloc[0])
            latest_date = str(Latest['DataModifica'].iloc[0])
            #get full order list (if any) - inner join with table Prodotti:
            query = f"SELECT ListeOrdini.CodiceProd, Prodotti.Nome, ListeOrdini.Quantità FROM ListeOrdini INNER JOIN Prodotti ON ListeOrdini.CodiceProd = Prodotti.CodiceProd WHERE ListeOrdini.CodiceOrd = {latest_code}"
            FullList = pd.read_sql(query, conn)
            if FullList.empty == False:
                num_prods = int(len(FullList.index))
                #convert to string:
                full_list = FullList.to_dict()
                full_list = json.dumps(full_list)

    except sqlite3.Error as e:
        log.error(f"Unable to perform get_existing_ordlist for supplier {supplier}. {e}")
        
    return latest_code, latest_date, full_list, num_prods


#b) create new order list from scratch in both DB tables:
def get_new_ordlist(conn, cursor, supplier):
    latest_code = None
    latest_date = None
    try:
        dt = datetime.now(pytz.timezone('Europe/Rome'))
        latest_code = int(dt.strftime('%Y%m%d%H%M%S')) #CodiceOrd = current datetime
        latest_date = str(dt.strftime('%Y-%m-%d')) #DataModifica initialized as current datetime
        #create order in StoricoOrdini:
        query = f"INSERT INTO StoricoOrdini (CodiceOrd, Produttore, DataModifica) VALUES ({latest_code}, '{supplier}', '{latest_date}')"
        cursor.execute(query)
        conn.commit()

    except sqlite3.Error as e:
        log.error(f"Unable to perform get_new_ordlist for supplier {supplier}. {e}")
        
    return latest_code, latest_date


#add a new product:
def add_prod(conn, cursor, utts):
    tup = (str(utts['p_code']), utts['supplier'], utts['p_name'], utts['category'])
    try:
        cursor.execute("INSERT INTO Prodotti (CodiceProd, Produttore, Nome, Categoria) VALUES (?, ?, ?, ?)", tup)
        log.info(f"Added product {utts['p_name']} to table Prodotti.")
    except sqlite3.Error as e:
        log.error(f"Unable to add product {utts['p_name']} to table Prodotti. {e}")

    conn.commit()
    return 0


#delete a product:
def delete_prod(conn, cursor, utts):
    p_name = utts['p_name']
    try:
        cursor.execute("DELETE FROM Prodotti WHERE Nome = ?", [p_name])
        log.info(f"Deleted product {utts['p_name']} from DB.")
    except sqlite3.Error as e:
        log.error(f"Unable to delete product {utts['p_name']} from DB. {e}")
    conn.commit()
    return 0


#MAIN:
if __name__ == '__main__':
    conn, cursor = db_connect()
    utts = {'p_code': 12345, 'p_name': 'flufast', 'supplier': 'biosline', 'category': 'health', 'pieces': 2}
    add_prod(conn, cursor, utts)
    utts = {'p_code': 12346, 'p_name': 'pappa reale fiale', 'supplier': 'aboca', 'category': 'health', 'pieces': 3}
    add_prod(conn, cursor, utts)
    utts = {'p_code': 12347, 'p_name': 'pappa reale bustine', 'supplier': 'aboca', 'category': 'health', 'pieces': 5}
    add_prod(conn, cursor, utts)
    utts = {'p_code': 12348, 'p_name': 'pappa reale compresse', 'supplier': 'biosline', 'category': 'health', 'pieces': 10}
    add_prod(conn, cursor, utts)
    utts = {'p_code': 12349, 'p_name': 'penne integrali kamut', 'supplier': 'fior di loto', 'category': 'food', 'pieces': 5}
    add_prod(conn, cursor, utts)
    # utts = {'p_name': 'pappa reale'}
    # print(get_prodinfo(conn, utts))
    # utts = {'p_name': 'pappa reale fiale'}
    # delete_prod(conn, cursor, utts)
    # utts['p_text'] = input("Insert prod name to find: ")
    # print(get_prodinfo(conn, utts))
    #s_text = input("Insert supplier name to find: ")
    # print(get_supplier(conn, s_text))
    conn.close()
