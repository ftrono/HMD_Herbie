from globals import *

#COMMON UTILITY FUNCTIONS:
# - readable_date()


#convert date to readable:
def readable_date(datestr):
    #orig date (format: '%Y-%m-%d'):
    comps = datestr.split('-')
    date_orig = date(int(comps[0]), int(comps[1]), int(comps[2]))
    mon = MONTHS[int(comps[1])-1]
    read_date = f"{int(comps[2])} {mon} {comps[0]}"

    #today:
    td = datetime.now(pytz.timezone('Europe/Rome'))
    td = td.strftime('%Y-%m-%d')
    comps_td = td.split('-')
    date_today = date(int(comps_td[0]), int(comps_td[1]), int(comps_td[2]))

    #datedif (in number of days):
    datedif = (date_today-date_orig).days

    #message:
    if datedif == 0:
        read_str = f"oggi"
    elif datedif == 1:
        read_str = f"ieri"
    elif datedif > 1 and datedif <= 15:
        read_str = f"{datedif} giorni fa, in data {read_date}"
    else:
        read_str = f"in data {read_date}"

    return read_str
