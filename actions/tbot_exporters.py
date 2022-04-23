import database.db_interactor as db_interactor
import database.db_export as db_export
from globals import *

#TBOT_EXPORTERS:
#common functions with Telegram bot:
# - create_view_prodotti()
# - create_view_recap()
# - create_view_listaordine()
# - create_view_storicoordini()


#EXPORT:
#view Prodotti:
def create_view_prodotti(filename, supplier=None):
    headers = {'Codice': 'codiceprod', 'Produttore': 'produttore', 'Nome': 'nome', 'Categoria': 'categoria', 'Quantita': 'quantita', 'Prezzo Pubblico €': 'prezzo', 'Sconto Medio %': 'scontomedio', 'IVA %': 'aliquota', 'Costo Acquisto €': 'costoacquisto', 'Costo Giacenze €': 'costototale', 'Valore Giacenze €': 'valoretotale', 'Disp Medico': 'dispmedico', 'Eta Minima': 'etaminima', ' Bio ': 'bio', ' Vegano ': 'vegano', 'Senza Glutine': 'senzaglutine', 'Senza Lattosio': 'senzalattosio', 'Senza Zucchero': 'senzazucchero'}
    #export table to pdf:
    try:
        Prodotti = db_export.get_view_prodotti(SCHEMA, supplier)
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
        elog.exception(f"Export error for xslx Prodotti for schema {SCHEMA}. {Exception}")
        return -1


#view Recap by produttore & categoria:
def create_view_recap(filename):
    headers = {'Produttore': 'produttore', 'Categoria': 'categoria', 'Sconto Medio %': 'scontomedio', 'IVA %': 'aliquota', 'Quantita': 'quantita', 'Costo Giacenze €': 'costototale', 'Valore Giacenze €': 'valoretotale'}
    #export table to pdf:
    try:
        Recap = db_export.get_view_recap()
        if Recap.empty == False:
            #1) format adjustments:
            Vista = pd.DataFrame(columns=headers.keys())
            for col in Vista.columns:
                if col in ['Sconto Medio %', 'IVA %']:
                    Vista[col] = Recap[headers[col]]/100
                elif col == 'Costo Giacenze €':
                    temp_inv = []
                    for ind in Recap.index:
                        discount = Recap['valoretotale'].iloc[ind] * (Recap['scontomedio'].iloc[ind]/100)
                        cost = Recap['valoretotale'].iloc[ind] - discount
                        cost = cost + (cost * (Recap['aliquota'].iloc[ind]/100))
                        temp_inv.append(cost)
                    Vista[col] = temp_inv
                else:
                    Vista[col] = Recap[headers[col]]
            #add grand totals row:
            Vista = Vista.append({col:'-' for col in Vista.columns}, ignore_index=True)
            Vista['Produttore'].iloc[-1] = 'TOTALE'
            Vista['Quantita'].iloc[-1] = Recap['quantita'].sum()
            Vista['Costo Giacenze €'].iloc[-1] = sum(temp_inv)
            Vista['Valore Giacenze €'].iloc[-1] = Recap['valoretotale'].sum()
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
                if column in ['Costo Giacenze €', 'Valore Giacenze €']:
                    writer.sheets[SCHEMA].set_column(first_col=col_idx, last_col=col_idx, width=column_width, cell_format=fmt_price)
                elif column in ['Sconto Medio %', 'IVA %']:
                    writer.sheets[SCHEMA].set_column(first_col=col_idx, last_col=col_idx, width=column_width, cell_format=fmt_pct)
                else:
                    writer.sheets[SCHEMA].set_column(first_col=col_idx, last_col=col_idx, width=column_width)
            writer.save()
        return 0
    except Exception:
        elog.exception(f"Export error for xslx Recap for schema {SCHEMA}. {Exception}")
        return -1


#view ListaOrdine by produttore or codiceord:
def create_view_listaordine(filename, supplier=None, codiceord=None):
    if not supplier and not codiceord:
        elog.error(f"create_view_listaordine() needs either a supplier or an order code.")
        return -1
    headers = {'Codice Prodotto': 'codiceprod', 'Produttore': 'produttore', 'Nome': 'nome', 'Categoria': 'categoria', 'Quantita Ordine': 'quantita', 'Prezzo Pubblico €': 'prezzo', 'Sconto Medio %': 'scontomedio', 'IVA %': 'aliquota', 'Costo Acquisto €': 'costoacquisto', 'Costo Totale €': 'costototale', 'Valore Totale €': 'valoretotale'}
    #export table to pdf:
    try:
        ListaOrdine = db_export.get_view_listaordine(supplier=supplier, codiceord=codiceord)
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
                if column in ['Prezzo Pubblico €', 'Costo Acquisto €', 'Costo Totale €', 'Valore Totale €']:
                    writer.sheets[SCHEMA].set_column(first_col=col_idx, last_col=col_idx, width=column_width, cell_format=fmt_price)
                elif column in ['Sconto Medio %', 'IVA %']:
                    writer.sheets[SCHEMA].set_column(first_col=col_idx, last_col=col_idx, width=column_width, cell_format=fmt_pct)
                else:
                    writer.sheets[SCHEMA].set_column(first_col=col_idx, last_col=col_idx, width=column_width)
            writer.save()
        return 0
    except Exception:
        elog.exception(f"Export error for xslx ListaOrdine {codiceord if codiceord else supplier} for schema {SCHEMA}. {Exception}")
        return -1


#view StoricoOrdini:
def create_view_storicoordini(filename):
    headers = {'Codice Ordine': 'codiceord', 'Produttore': 'produttore', 'Riferimento': 'riferimento', 'Data Modifica': 'datamodifica', 'Data Inoltro': 'datainoltro', 'Data Ricezione': 'dataricezione'}
    #export table to pdf:
    try:
        Storico = db_export.get_view_storicoordini()
        if Storico.empty == False:
            #1) format adjustments:
            Vista = pd.DataFrame(columns=headers.keys())
            for col in Vista.columns:
                if col == 'Codice Ordine':
                    Vista[col] = [str(p_code) for p_code in Storico[headers[col]]]
                else:
                    Vista[col] = Storico[headers[col]]
            Vista.reset_index(drop=True, inplace=True)

            #2) export:
            #load Pandas Excel exporter:
            writer = pd.ExcelWriter(filename)
            Vista.to_excel(writer, sheet_name=SCHEMA, index=False, na_rep='')
            #auto-adjust columns' width:
            for column in Vista:
                column_width = max(Vista[column].astype(str).map(len).max(), len(column))
                col_idx = Vista.columns.get_loc(column)
                writer.sheets[SCHEMA].set_column(first_col=col_idx, last_col=col_idx, width=column_width)
            writer.save()
        return 0
    except Exception:
        elog.exception(f"Export error for xslx StoricoOrdini for schema {SCHEMA}. {Exception}")
        return -1
