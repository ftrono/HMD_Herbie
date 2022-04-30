from globals import *
import actions.commons as commons

#PRODUCTS:
# - read_compatibility()
# - read_prodinfo()
# - read_cat_vat()
# - read_vegan()
# - read_nolactose()
# - read_nogluten()
# - read_nosugar()


#joint: product info:
def read_compatibility(vegan, nolactose, nogluten, nosugar):
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
    if slots['dispmedico'] == 'true':
        read_disp = "E' un dispositivo medico."
    else:
        read_disp = "Non è un dispositivo medico."
    message = f"{slots['p_name']} è un prodotto di {slots['supplier']}, categoria {slots['category']}. {read_disp} Il prezzo di listino è {commons.readable_price(slots['price'])} e include l'IVA al {slots['vat']}%. {read_compatibility(slots['vegan'], slots['no_lactose'], slots['no_gluten'], slots['no_sugar'])}"
    return message


#separate: product info:
def read_cat_vat(category, vat):
    message = f"Il prodotto appartiene alla categoria {category}, con IVA al {vat}%."
    return message

def read_dispmedico(dispmedico):
    if dispmedico == 'true':
        message = "Il prodotto è un dispositivo medico."
    else:
        message = "Il prodotto non è un dispositivo medico."
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
