import math
from globals import *

#PRODUCTS:
# - readable_price()
# - read_allergens()
# - read_prodinfo()
# - read_cat_vat()
# - read_vegan()
# - read_nolactose()
# - read_nogluten()
# - read_nosugar()

#readable price:
def readable_price(price):
    price = float(price)
    #modf -> returns a tuple with (decimal part, integer part):
    parts = math.modf(price)
    #integer part:
    pricestr = f"{int(parts[1])} Euro"
    #decimal part:
    decs = int(parts[0]*100)
    if decs != 0:
        pricestr = f"{pricestr} e {decs}"
    return pricestr

#joint: product info:
def read_allergens(vegan, nolactose, nogluten, nosugar):
    message = "Il prodotto"
    if vegan == 'true':
        message = f"{message} è vegano, dunque è senza lattosio;"
    else:
        message = f"{message} non è vegano;"
        if nolactose == 'true':
            message = f"{message} è senza lattosio,"
        else:
            message = f"{message} contiene lattosio, "
    if nogluten == 'true':
        message = f"{message} è senza glutine e"
    else:
        message = f"{message} contiene glutine e"
    if nosugar == 'true':
        message = f"{message}d è senza zucchero."
    else:
        message = f"{message} contiene zucchero."
    return message

def read_prodinfo(slots):
    message = f"{slots['p_name']} è un prodotto di {slots['supplier']}, categoria {slots['category']}. Il prezzo di listino è {readable_price(slots['price'])} e include l'IVA al {slots['vat']}%. {read_allergens(slots['vegan'], slots['no_lactose'], slots['no_gluten'], slots['no_sugar'])}"
    return message


#separate: product info:
def read_cat_vat(category, vat):
    message = f"Il prodotto appartiene alla categoria {category}, con IVA al {vat}%."
    return message

def read_vegan(vegan):
    if vegan == 'true':
        message = "Il prodotto è vegano."
    else:
        message = "Il prodotto non è vegano."
    return message

def read_nolactose(vegan, nolactose):
    if vegan == 'true':
        message = "Il prodotto è vegano, dunque è senza lattosio."
    elif nolactose == 'true':
        message = "Il prodotto è senza lattosio."
    else:
        message = "Il prodotto contiene lattosio."
    return message

def read_nogluten(nogluten):
    if nogluten == 'true':
        message = "Il prodotto è senza glutine."
    else:
        message = "Il prodotto contiene glutine."
    return message

def read_nosugar(nosugar):
    if nosugar == 'true':
        message = "Il prodotto è senza zucchero."
    else:
        message = "Il prodotto contiene zucchero."
    return message
