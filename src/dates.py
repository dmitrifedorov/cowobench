'''
Created on Apr 15, 2018

@author: Dmitri Fedorov
'''

import calendar, datetime

def main(year = 2018, months = range(4, 13)):
    
    my_calendar = calendar.Calendar(6)

    def get_days():
        for month in months:
            for curr_day in my_calendar.itermonthdates(year, month):
                yield curr_day

    def get_cycle_days(seed):
        curr_from_date, delta = seed
        for month in months:
            for curr_day in my_calendar.itermonthdates(year, month):
                if curr_day == (curr_from_date + delta):
                    curr_from_date = curr_day
                    yield curr_day

    cycle1 = [d for d in get_cycle_days((datetime.date(year=2018, month=4, day=13), datetime.timedelta(weeks=2)))]
    cycle2 = [d for d in get_cycle_days((datetime.date(year=2018, month=4, day=23), datetime.timedelta(weeks=2)))]
    
    dates = []
    for curr_day in get_days():
        add_it = (curr_day in cycle1 or curr_day in cycle2) or (curr_day.day == 16) or (curr_day.day == 1) or (curr_day.day == calendar.monthrange(curr_day.year, curr_day.month)[1])
        if add_it:
            add_day = curr_day
            add_curr = False
            print(add_day.strftime('%d/%m/%Y'), add_day.weekday())
            while add_day.weekday() in [5,6]:
                add_day = add_day - datetime.timedelta(days=1)
                add_curr = True
            if not add_day in dates:
                dates.append(add_day)
            if add_curr and not curr_day in dates:
                dates.append(curr_day)
                
    print(','.join([x.strftime('%d/%m/%Y') for x in dates]))



if __name__ == '__main__':
    main()