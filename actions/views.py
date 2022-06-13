import database.db_export as db_export
from globals import *

#TBOT_VIEWS:
#common functions with Telegram bot:
# - create_view_prodotti()
# - create_view_listaordine()
# - create_view_storicoordini()


#EXPORT:
#view Prodotti:
def create_view_prodotti(filename, supplier=None):
    headers = {'Codice': 'codiceprod', 'Produttore': 'produttore', 'Nome': 'nome', 'Categoria': 'categoria', 'Quantita': 'quantita', 'Prezzo Pubblico €': 'prezzo', 'Sconto Medio %': 'scontomedio', 'IVA %': 'aliquota', 'Costo Acquisto €': 'costoacquisto', 'Costo Giacenze €': 'costototale', 'Valore Giacenze €': 'valoretotale', 'Disp Medico': 'dispmedico', ' Vegano ': 'vegano', 'Senza Lattosio': 'senzalattosio', 'Senza Glutine': 'senzaglutine', 'Senza Zucchero': 'senzazucchero'}
    #export table to pdf:
    try:
        Prodotti = db_export.get_view_prodotti(supplier)
        if Prodotti.empty == False:
            #1) format adjustments:
            Vista = pd.DataFrame(columns=headers.keys())
            for col in Vista.columns:
                if col == 'Codice':
                    Vista[col] = [str(p_code) for p_code in Prodotti[headers[col]]]
                elif col in ['Sconto Medio %', 'IVA %']:
                    Vista[col] = Prodotti[headers[col]]/100
                elif col == 'Costo Acquisto €':
                    #calculate purchase cost & inventory value from available data:
                    temp_cost = []
                    temp_inv = []
                    for ind in Prodotti.index:
                        #purchase cost:
                        discount = Prodotti['prezzo'].iloc[ind] * (Prodotti['scontomedio'].iloc[ind]/100)
                        cost = Prodotti['prezzo'].iloc[ind] - discount
                        cost = cost + (cost * (Prodotti['aliquota'].iloc[ind]/100))
                        temp_cost.append(cost)
                        #inventory value:
                        inventory = cost * Prodotti['quantita'].iloc[ind]
                        temp_inv.append(inventory)
                    Vista[col] = temp_cost
                elif col == 'Costo Giacenze €':
                    #populate column with the inventory value (at cost) already calculated:
                    Vista[col] = temp_inv
                else:
                    Vista[col] = Prodotti[headers[col]]
            
            Vista.replace(to_replace=False, value='No', inplace=True)
            Vista.replace(to_replace=True, value='Sì', inplace=True)
            #add grand totals row:
            Vista = Vista.append({col:'-' for col in Vista.columns}, ignore_index=True)
            Vista['Codice'].iloc[-1] = 'TOTALE'
            Vista['Quantita'].iloc[-1] = Prodotti['quantita'].sum()
            Vista['Costo Giacenze €'].iloc[-1] = sum(temp_inv)
            Vista['Valore Giacenze €'].iloc[-1] = Prodotti['valoretotale'].sum()
            Vista.reset_index(drop=True, inplace=True)

            #2) export:
            #load Pandas Excel exporter:
            writer = pd.ExcelWriter(filename)
            Vista.to_excel(writer, sheet_name=SCHEMA, index=False, na_rep='')
            workbook  = writer.book
            fmt_price = workbook.add_format({'num_format': '#,##0.00'})
            fmt_pct = workbook.add_format({'num_format': '0%'})
            #auto-adjust columns' width:
            for column in Vista:
                column_width = max(Vista[column].astype(str).map(len).max(), len(column))
                col_idx = Vista.columns.get_loc(column)
                if column in ['Prezzo Pubblico €', 'Costo Acquisto €', 'Costo Giacenze €', 'Valore Giacenze €']:
                    writer.sheets[SCHEMA].set_column(first_col=col_idx, last_col=col_idx, width=column_width, cell_format=fmt_price)
                elif column in ['Sconto Medio %', 'IVA %']:
                    writer.sheets[SCHEMA].set_column(first_col=col_idx, last_col=col_idx, width=column_width, cell_format=fmt_pct)
                else:
                    writer.sheets[SCHEMA].set_column(first_col=col_idx, last_col=col_idx, width=column_width)
            writer.save()
        return 0
    except Exception:
        elog.exception(f"create_view_prodotti(): Export error for xslx Prodotti for schema {SCHEMA}. {Exception}")
        return -1


#view ListaOrdine by codiceord:
def create_view_listaordine(codiceord):
    headers = {'Codice Prodotto': 'codiceprod', 'Produttore': 'produttore', 'Nome': 'nome', 'Categoria': 'categoria', 'Quantita Ordine': 'quantita', 'Prezzo Pubblico €': 'prezzo', 'Sconto Medio %': 'scontomedio', 'IVA %': 'aliquota', 'Costo Acquisto €': 'costoacquisto', 'Costo Totale €': 'costototale', 'Valore Totale €': 'valoretotale'}
    #export table to pdf:
    try:
        ListaOrdine = db_export.get_view_listaordine(codiceord)
        if ListaOrdine.empty == False:
            #1) format adjustments:
            Vista = pd.DataFrame(columns=headers.keys())
            for col in Vista.columns:
                if col == 'Codice Prodotto':
                    Vista[col] = [str(p_code) for p_code in ListaOrdine[headers[col]]]
                elif col in ['Sconto Medio %', 'IVA %']:
                    Vista[col] = ListaOrdine[headers[col]]/100
                elif col == 'Costo Acquisto €':
                    #calculate unit cost and total cost from available data:
                    temp_cost = []
                    temp_totcost = []
                    temp_totprice = []
                    for ind in ListaOrdine.index:
                        #unit cost:
                        discount = ListaOrdine['prezzo'].iloc[ind] * (ListaOrdine['scontomedio'].iloc[ind]/100)
                        cost = ListaOrdine['prezzo'].iloc[ind] - discount
                        cost = cost + (cost * (ListaOrdine['aliquota'].iloc[ind]/100))
                        temp_cost.append(cost)
                        #total cost:
                        totcost = cost * ListaOrdine['quantita'].iloc[ind]
                        temp_totcost.append(totcost)
                        #total price:
                        totprice = ListaOrdine['prezzo'].iloc[ind] * ListaOrdine['quantita'].iloc[ind]
                        temp_totprice.append(totprice)
                    Vista[col] = temp_cost
                elif col == 'Costo Totale €':
                    #populate column with the inventory value (at cost) already calculated:
                    Vista[col] = temp_totcost
                elif col == 'Valore Totale €':
                    #populate column with the inventory value (at cost) already calculated:
                    Vista[col] = temp_totprice
                else:
                    Vista[col] = ListaOrdine[headers[col]]
            
            #add grand totals row:
            Vista = Vista.append({col:'-' for col in Vista.columns}, ignore_index=True)
            Vista['Codice Prodotto'].iloc[-1] = 'TOTALE'
            Vista['Quantita Ordine'].iloc[-1] = ListaOrdine['quantita'].sum()
            Vista['Costo Totale €'].iloc[-1] = sum(temp_totcost)
            Vista['Valore Totale €'].iloc[-1] = sum(temp_totprice)
            Vista.reset_index(drop=True, inplace=True)
            supplier = Vista['Produttore'].iloc[0]
            codedate = str(codiceord) if len(str(codiceord)) < 8 else str(codiceord)[:8]

            #2) export:
            #load Pandas Excel exporter:
            filename = f'./actions/data_cache/{SCHEMA}.lista_{supplier}_{codedate}.xlsx'
            writer = pd.ExcelWriter(filename)
            Vista.to_excel(writer, sheet_name=SCHEMA, index=False, na_rep='')
            workbook  = writer.book
            fmt_price = workbook.add_format({'num_format': '#,##0.00'})
            fmt_pct = workbook.add_format({'num_format': '0%'})
            #auto-adjust columns' width:
            for column in Vista:
                column_width = max(Vista[column].astype(str).map(len).max(), len(column))
                col_idx = Vista.columns.get_loc(column)
                if column in ['Prezzo Pubblico €', 'Costo Acquisto €', 'Costo Totale €', 'Valore Totale €']:
                    writer.sheets[SCHEMA].set_column(first_col=col_idx, last_col=col_idx, width=column_width, cell_format=fmt_price)
                elif column in ['Sconto Medio %', 'IVA %']:
                    writer.sheets[SCHEMA].set_column(first_col=col_idx, last_col=col_idx, width=column_width, cell_format=fmt_pct)
                else:
                    writer.sheets[SCHEMA].set_column(first_col=col_idx, last_col=col_idx, width=column_width)
            writer.save()
        return 0, supplier, filename
    except Exception:
        elog.exception(f"create_view_listaordine(): Export error for xslx ListaOrdine {codiceord} for schema {SCHEMA}. {Exception}")
        return -1, None, ""


#extract view and send it via tBot:
def get_vista(caller, filter=None):
    try:
        #forker:
        if caller == 'lista':
            ordcode = int(filter)
            ret, suppl, filename = create_view_listaordine(ordcode)
            filetype = f"la lista ordine per {suppl}"
        else:
            filename = f'./actions/data_cache/{SCHEMA}.{caller}{f"_{filter}" if filter else ""}.xlsx'
            ret = create_view_prodotti(filename, filter)
            filetype = f"la vista delle giacenze{f' di {filter}' if filter else ''}"
        #result:
        if ret == 0:
            #send file to user:
            try:
                ids = db_export.get_chat_IDs()
                elog.info(f"{ids}")
                for chat_id in ids:
                    xlsx = open(filename, 'rb')
                    TBOT.sendDocument(chat_id=chat_id, document=xlsx)
                    xlsx.close()
                os.remove(filename)
                message = f"Ti ho inviato {filetype} su Telegram, pronta per la stampa. Dai un'occhiata!"
                ret = 0
            except Exception as e:
                message = f"Non ho trovato dati."
                elog.error(f"get_vista(): {e}")
                ret = -1
        else:
            message = f"Non ho trovato viste corrispondenti."
            ret = -1
    except Exception as e:
        message = f"C'è stato un problema, ti chiedo scusa!"
        elog.error(f"get_vista(): {e}")
        ret = -1
    return ret, message
