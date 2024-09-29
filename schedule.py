# Store the calendar link in cals.txt
def store_calendar_link(link: str):
    with open('cals.txt', 'a') as file:
        file.write(link + '\n')