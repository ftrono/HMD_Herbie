from globals import *
from db_tools import db_connect

#DB_INTERACTIONS:
# - add_prod()
# - get_prodinfo()
# - get_quantity()
# - delete_prod()


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
            log.error("DB query error for 'p_code'. {}".format(e))

    else:
        #tokenize p_text to extract p_name:
        p_text = utts['p_text'].strip()
        tokens = p_text.split()
        print(tokens)

        #get list of suppliers:
        try:
            query = "SELECT DISTINCT Produttore FROM Prodotti"
            Suppliers = pd.read_sql(query, conn)
        except sqlite3.Error as e:
            log.error("DB query error for 'supplier'. {}".format(e))

        suppl_tok = ''

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
            for ind in to_pop:
                tokens.pop(ind)
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
                log.error("DB query error for p_name. {}".format(e))

        #reduce tokens list:
        if to_pop != []:
            for ind in to_pop:
                tokens.pop(ind)
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


#get product reference from DB:
def get_p_code_from_ent(tracker, dispatcher):
    
    utts = {}
    #get latest entity values from tracker, or None if they're not available:
    utts['p_code'] = next(tracker.get_latest_entity_values("p_code"), None)
    if utts['p_code'] != None:
        utts['p_code'] = str(utts['p_code']).lower()

    utts['p_name'] = next(tracker.get_latest_entity_values("p_name"), None)
    if utts['p_name'] != None:
        utts['p_name'] = utts['p_name'].lower()
        
    utts['supplier'] = next(tracker.get_latest_entity_values("supplier"), None)
    if utts['supplier'] != None:
        utts['supplier'] = utts['supplier'].lower()

    #fallback: under informative:
    # - case a) no info
    # - case b) p_code (it's self-sufficient)
    # - case c) p_name + supplier
    if utts['p_name'] == None and utts['p_code'] == None:
        message = f"Mmm, mi manca qualche informazione."
        message = "Puoi leggermi il codice a barre, oppure dirmi il nome del prodotto e il produttore!"
        return None
    
    #db extraction:
    try:
        conn, cursor = db_connect()   
        resp = get_prodinfo(conn, utts)
        conn.close()
    except:
        resp == []
    
    #fallback: not found:
    if resp == []:
        if utts['p_code'] != None:
            str1 = "codice"
        else:
            str1 = "nome"
        message = f"Non ho trovato nessun prodotto con questo " + str1 + ". Riproviamo!"
        dispatcher.utter_message(text=message)
        return None

    elif len(resp) > 1:
        message = f"Ho trovato più di un prodotto simile:"
        for prod in resp:
            message = message + "\nDi " + prod['supplier'] + ", " + prod['p_name'] + "."
        message = message + "\nProva a specificare meglio!"
        dispatcher.utter_message(text=message)
        return None

    else:
        prod = resp[0]
        message = f"Trovato! Di {prod['supplier']}, {prod['p_name']}."
        dispatcher.utter_message(text=message)
        return prod


#MAIN:
if __name__ == '__main__':
    conn, cursor = db_connect()
    # utts = {'p_code': 12345, 'p_name': 'flufast', 'supplier': 'biosline', 'category': 'health', 'quantity': 2}
    # add_prod(conn, cursor, utts)
    # utts = {'p_code': 12346, 'p_name': 'pappa reale fiale', 'supplier': 'aboca', 'category': 'health', 'quantity': 3}
    # add_prod(conn, cursor, utts)
    # utts = {'p_code': 12347, 'p_name': 'pappa reale bustine', 'supplier': 'aboca', 'category': 'health', 'quantity': 5}
    # add_prod(conn, cursor, utts)
    # utts = {'p_code': 12348, 'p_name': 'pappa reale compresse', 'supplier': 'biosline', 'category': 'health', 'quantity': 10}
    # add_prod(conn, cursor, utts)
    # utts = {'p_name': 'pappa reale'}
    # print(get_prodinfo(conn, utts))
    # utts = {'p_name': 'pappa reale fiale'}
    # delete_prod(conn, cursor, utts)
    utts = {'p_text': None, 'p_code': None}
    utts['p_text'] = input("Insert prod name to find: ")
    print(get_prodinfo(conn, utts))
    conn.close()
