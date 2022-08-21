from globals import *
from database.db_tools import db_connect, db_disconnect

#DB_INTERACTOR:
#Low-level DB interfaces:
# - match_product()
# - match_supplier()
# - update_pieces()
# - delete_ordlist()
# - get_json_ordlist()
# - get_new_ordlist()
# - get_suggestion_list()
# - mark_definitive()
# - check_closed()
# - register_delivered()


#find matching product and get info (ret -> DataFrame):
def match_product(p_text, supplier=None):
    Prodotti = pd.DataFrame()
    #extract data from DB:
    suppstr = ""
    if supplier:
        suppstr = f"WHERE prodotti.produttore = '{supplier}'"
    try:
        conn, cursor = db_connect()
        query = f"SELECT prodotti.*, produttori.scontomedio, categorie.aliquota FROM {SCHEMA}.prodotti INNER JOIN {SCHEMA}.produttori ON prodotti.produttore = produttori.produttore INNER JOIN {SCHEMA}.categorie ON prodotti.categoria = categorie.categoria {suppstr}"
        Prodotti = pd.read_sql(query, conn)
        db_disconnect(conn, cursor)
    except Exception as e:
        dlog.error(f"match_product(): DB query error for 'p_text'. {e}")
        return Prodotti
    
    #analyze string similarity for each name:
    p_text = p_text.strip()
    matches = {}
    for ind in Prodotti.index:
        name = ""
        #if supplier not passed as arg -> search jointly in columns supplier and name:
        if not supplier:
            name = f"{Prodotti['produttore'].iloc[ind]} "
        name = f"{name}{Prodotti['nome'].iloc[ind]}"
        #set similarity ratio:
        matches[ind] = fuzz.token_set_ratio(p_text, name)
    
    #fiter the dict keeping only the 3 items with the highest similarity:
    matches = dict(sorted(matches.items(), key=lambda item: item[1], reverse=True)[:3])
    inds = list(matches.keys())
    #if 0 good matches (less 20% confidence) -> return empty dataframe:
    if matches[inds[0]] <= 20:
        Matches = pd.DataFrame()
        return Matches
    #elif 1 good match -> return it:
    elif len(inds) < 2:
        Matches = Prodotti.iloc[inds]
        return Matches
    #else: apply similarity threshold (delta > 10%):
    elif matches[inds[0]] > matches[inds[1]]+10:
        inds = [inds[0]]
    Matches = Prodotti.iloc[inds]
    Matches.reset_index(drop=True, inplace=True)
    return Matches


#find matching supplier (ret -> List):
def match_supplier(s_text):
    #extract data from DB:
    try:
        conn, cursor = db_connect()
        query = f"SELECT produttore FROM {SCHEMA}.produttori"
        suppliers = pd.read_sql(query, conn)
        suppliers = suppliers['produttore'].to_list()
        db_disconnect(conn, cursor)
    except Exception as e:
        suppliers = []
        dlog.error(f"match_supplier(): DB query error for 'supplier'. {e}")
        return suppliers
    
    #analyze string similarity for each name:
    s_text = s_text.strip()
    matches = {}
    for ind in range(len(suppliers)):
        #set similarity ratio:
        matches[ind] = fuzz.token_set_ratio(s_text, suppliers[ind])
    
    #fiter the dict keeping only the 3 items with the maximum frequency found:
    matches = dict(filter(lambda elem: elem[1] == max(matches.values()), matches.items()))
    results = []
    for ind in list(matches.keys()):
        results.append(suppliers[ind])
    return results


#update quantities in DB:
def update_pieces(utts):
    #compose query:
    if utts['variation'] == 'add':
        str1 = f"+ {utts['pieces']}"
    elif utts['variation'] == 'decrease':
        str1 = f"- {utts['pieces']}"
    else:
        return -1
    query = f"UPDATE {SCHEMA}.prodotti SET quantita = quantita {str1} WHERE codiceprod = {utts['p_code']}"

    #DB update:
    try:
        conn, cursor = db_connect()
        cursor.execute(query)
        changes = cursor.rowcount
        if changes != 0:
            conn.commit()
            db_disconnect(conn, cursor)
            dlog.info(f"update_pieces(): Success: {utts['variation']} {utts['pieces']} pieces to product code {utts['p_code']}.")
            return 0
        else:
            db_disconnect(conn, cursor)
            dlog.error(f"update_pieces(): No match for p_code {utts['p_code']}.")
            return -1
    except Exception as e:
        dlog.error(f"update_pieces(): Unable to perform operation {utts['variation']} to product code {utts['p_code']}. {e}")
        return -1


#delete an existent ord_list:
def delete_ordlist(ord_code, conn=None, cursor=None):
    reconnect = False if conn else True
    try:
        if reconnect == True:
            conn, cursor = db_connect()
        query = f"DELETE FROM {SCHEMA}.listeordini WHERE codiceord = {ord_code}"
        cursor.execute(query)
        query = f"DELETE FROM {SCHEMA}.storicoordini WHERE codiceord = {ord_code}"
        cursor.execute(query)
        conn.commit()
        if reconnect == True:
            db_disconnect(conn, cursor)
        dlog.info(f"delete_ordlist(): Success: deleted ord_list code {ord_code} from both tables listeordini and storicoordini.")
        return 0
    except Exception as e:
        dlog.error(f"delete_ordlist(): Unable to delete ord_list code {ord_code}. {e}")
        return -1


#extract from DB latest order list in JSON for the current supplier (if any):
def get_json_ordlist(conn, supplier, closed=False):
    latest_code = None
    latest_date = None
    full_list = None
    num_prods = 0
    try:
        openstr = "FALSE" if closed==False else "TRUE"
        query = f"SELECT codiceord, datamodifica FROM {SCHEMA}.storicoordini WHERE produttore = '{supplier}' AND definitiva = {openstr} ORDER BY datamodifica DESC LIMIT 1"
        Latest = pd.read_sql(query, conn)
        if Latest.empty == False:
            #extract references:
            latest_code = int(Latest['codiceord'].iloc[0])
            latest_date = str(Latest['datamodifica'].iloc[0])
            #get full order list (if any) - inner join with table prodotti:
            query = f"SELECT listeordini.codiceprod, prodotti.nome, listeordini.quantita, prodotti.quantita AS giacenza FROM {SCHEMA}.listeordini INNER JOIN {SCHEMA}.prodotti ON listeordini.codiceprod = prodotti.codiceprod WHERE listeordini.codiceord = {latest_code}"
            FullList = pd.read_sql(query, conn)
            if FullList.empty == False:
                num_prods = int(len(FullList.index))
                #convert to string:
                full_list = FullList.to_dict()
                full_list = json.dumps(full_list)
    except Exception as e:
        dlog.error(f"get_json_ordlist(): Unable to perform get_json_ordlist for supplier {supplier}. {e}")
    return latest_code, latest_date, full_list, num_prods


#create new order list from scratch in both DB tables:
def get_new_ordlist(conn, cursor, supplier):
    latest_code = None
    latest_date = None
    try:
        dt = datetime.now(pytz.timezone('Europe/Rome'))
        latest_code = int(dt.strftime('%Y%m%d%H%M%S')) #codiceord = current datetime
        latest_date = str(dt.strftime('%Y-%m-%d')) #datamodifica initialized as current datetime
        #create order in storicoordini:
        query = f"INSERT INTO {SCHEMA}.storicoordini (codiceord, produttore, datamodifica) VALUES ({latest_code}, '{supplier}', '{latest_date}')"
        cursor.execute(query)
        conn.commit()
        dlog.info(f"get_new_ordlist(): Success: created list ord_code {latest_code} into table storicoordini.")
    except Exception as e:
        dlog.error(f"get_new_ordlist(): Unable to perform get_new_ordlist for supplier {supplier}. {e}")
    return latest_code


#edit order list:
def edit_ord_list(conn, cursor, ord_code, p_code, pieces, write_mode=False):
    try:
        #a) write_mode ("insert into"):
        if write_mode == True:
            #check first: avoid double inclusion of a product:
            query = f"SELECT codiceprod FROM {SCHEMA}.listeordini WHERE codiceord = {ord_code} AND codiceprod = {p_code}"
            Prod = pd.read_sql(query, conn)
            if Prod.empty == False:
                #if product already there, update quantity:
                query = f"UPDATE {SCHEMA}.listeordini SET quantita = {pieces} WHERE codiceord = {ord_code} AND codiceprod = {p_code}"
            else:
                #insert new row with the product:
                query = f"INSERT INTO {SCHEMA}.listeordini (codiceord, codiceprod, quantita) VALUES ({ord_code}, {p_code}, {pieces})"

        #b) update mode ("update set" or "delete from"):
        elif pieces == 0:
            query = f"DELETE FROM {SCHEMA}.listeordini WHERE codiceord = {ord_code} AND codiceprod = {p_code}"
        else:
            query = f"UPDATE {SCHEMA}.listeordini SET quantita = {pieces} WHERE codiceord = {ord_code} AND codiceprod = {p_code}"
            
        cursor.execute(query)
        #update last_modified date:
        dt = datetime.now(pytz.timezone('Europe/Rome'))
        latest_date = str(dt.strftime('%Y-%m-%d')) #datamodifica initialized as current datetime
        query = f"UPDATE {SCHEMA}.storicoordini SET datamodifica = '{latest_date}' WHERE codiceord = {ord_code}"
        cursor.execute(query)
        conn.commit()
        dlog.info(f"edit_ord_list(): Success: updated list ord_code {ord_code} into table listeordini.")
        return 0
    except Exception as e:
        dlog.error(f"edit_ord_list(): Unable to edit ord_list {ord_code} for product {p_code}. {e}")
        return -1


#get list of suggestions from DB:
def get_suggestion_list(conn, supplier, ord_code):
    full_list = None
    num_prods = 0
    try:
        #extract list of prods from the requested suppliers, with Quantità <= threshold and that have not been added yet to the order list under preparation:
        query = f"SELECT prodotti.codiceprod, prodotti.nome, prodotti.quantita FROM {SCHEMA}.prodotti WHERE prodotti.produttore = '{supplier}' AND prodotti.quantita <= {THRESHOLD_TO_ORD} AND NOT EXISTS (SELECT listeordini.codiceprod FROM {SCHEMA}.listeordini WHERE listeordini.codiceord = {ord_code} AND listeordini.codiceprod = prodotti.codiceprod) ORDER BY prodotti.quantita"
        FullList = pd.read_sql(query, conn)
        if FullList.empty == False:
            num_prods = int(len(FullList.index))
            #convert to string:
            full_list = FullList.to_dict()
            full_list = json.dumps(full_list)
    except Exception as e:
        dlog.error(f"get_suggestion_list(): Unable to perform get_suggestion_list for supplier {supplier}. {e}")
    return full_list, num_prods


#mark an order list as definitive:
def mark_definitive(ord_code):
    try:
        conn, cursor = db_connect()
        query = f"UPDATE {SCHEMA}.storicoordini SET definitiva = TRUE WHERE codiceord = {ord_code}"
        cursor.execute(query)
        conn.commit()
        db_disconnect(conn, cursor)
        dlog.info(f"mark_definitive(): Success: marked ord_list code {ord_code} as definitive.")
        return 0
    except Exception as e:
        dlog.error(f"mark_definitive(): Unable to mark ord_list code {ord_code} as definitive. {e}")
        return -1


#check if present closed orders:
def check_closed():
    num_closed = 0
    try:
        conn, cursor = db_connect()
        query = f"SELECT codiceord FROM {SCHEMA}.storicoordini WHERE definitiva = TRUE"
        Orders = pd.read_sql(query, conn)
        if Orders.empty == False:
            num_closed = len(Orders.index)
        db_disconnect(conn, cursor)
    except Exception as e:
        dlog.error(f"check_closed(): Unable to check for closed orders. {e}")
    return num_closed

#mark an order list as definitive:
def register_delivered(closed_code, closed_list):
    try:
        #unpack JSON string to DataFrame:
        OrdList = json.loads(closed_list)
        OrdList = pd.DataFrame(OrdList)
        OrdList.reset_index(drop=True, inplace=True)
        #update prod quantity in warehouse (var = ordered pieces):
        conn, cursor = db_connect()
        for ind in OrdList.index:
            pieces = OrdList['quantita'].iloc[ind]
            query = f"UPDATE {SCHEMA}.prodotti SET quantita = quantita + {pieces} WHERE codiceprod = {OrdList['codiceprod'].iloc[ind]}"
            cursor.execute(query)
        conn.commit()
        db_disconnect(conn, cursor)
        dlog.info(f"register_delivered(): Success: registered delivery of ord_list code {closed_code}.")
        return 0
    except Exception as e:
        dlog.error(f"register_delivered(): Unable to register delivery of ord_list code {closed_code}. {e}")
        return -1
