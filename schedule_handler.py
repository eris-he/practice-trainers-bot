import discord
from datetime import datetime, timedelta
import schedule as scheduler
from ics import Calendar
import pytz
import requests
from collections import defaultdict
from datetime import timedelta
import re
import aiohttp
import asyncio

MAX_FIELD_LENGTH = 1024
MAX_EMBED_FIELDS = 25

# Function to store the calendar link in cals.txt
def store_calendar_link(link: str):
    if not link.strip():
        return  
    with open('cals.txt', 'a') as file:
        file.write(link + '\n')

# Function to read stored calendar links
def get_calendar_links():
    with open('cals.txt', 'r') as file:
        links = [line.strip() for line in file.readlines()]
    
    updated_links = []
    for link in links:
        if not link.startswith(('http://', 'https://')):
            updated_links.append(f'http://{link}')
        else:
            updated_links.append(link)
    
    return updated_links

# Function to fetch the calendar data from a link
async def fetch_calendar(link):
    async with aiohttp.ClientSession() as session:
        async with session.get(link) as response:
            if response.status == 200:
                return await response.text()
            else:
                return None

# Function to extract the trainer's name from the calendar link
def extract_trainer_name(link: str) -> str:
    # Extract the name portion after the '/t/' in the URL
    match = re.search(r'/t/([^/]+)', link)
    if match:
        # Get the raw trainer name (without formatting)
        trainer_name = match.group(1)
        # Insert a space before any capital letter after the first one
        formatted_name = re.sub(r'(?<!^)(?=[A-Z])', ' ', trainer_name)
        return formatted_name
    return "Unknown Trainer"

# Function to extract the city and state from the location if in the format "Street Address, City, State"
def extract_city_state(location: str) -> str:
    # Regex pattern to match ", City, State" (ignores street address if present)
    match = re.search(r',\s*([A-Za-z\s]+),\s*([A-Za-z\s]+)$', location)
    if match:
        city = match.group(1)
        state = match.group(2)
        return f"{city}, {state}"
    return location  # Return the whole location if no match is found

# Function to get upcoming events for the next week from .ics calendars
def get_events_for_next_week(link: str):
    response = requests.get(link)
    if response.status_code == 200:
        cal = Calendar(response.text)
        now = datetime.now(pytz.timezone('US/Eastern'))
        one_week_later = now + timedelta(weeks=1)
        events = []
        for event in cal.events:
            if now <= event.begin.datetime <= one_week_later:
                events.append(event)
        return events
    else:
        return []


# Function to get events for a specific period (day, week, month)
async def get_calendar_events(period: str):
    events_by_trainer = {}  # Dictionary to store events by trainer
    days = 1  # Default to 1 day
    links = get_calendar_links()  # Get calendar links from cals.txt
    print(f"Links: {links}")
    
    now = datetime.now(pytz.timezone('US/Eastern'))
    
    # Define the time range based on the period
    if period == "day":
        end_time = now + timedelta(days=1)
    elif period == "week":
        end_time = now + timedelta(weeks=1)
        days = 7
    elif period == "month":
        end_time = now + timedelta(days=30)  # Approximation of a month
        days = 30
    
    # Reason why I can't use this: I grab the name of the trainer from the link smh
    # tasks = [fetch_calendar(link) for link in links]
    # calendar_responses = await asyncio.gather(*tasks)

    for link in links:
        response = requests.get(link)
        if response.status_code == 200:
            cal = Calendar(response.text)
            trainer_name = extract_trainer_name(link)
            
            if trainer_name not in events_by_trainer:
                events_by_trainer[trainer_name] = []

            for event in cal.events:
                if now <= event.begin.datetime <= end_time:
                    location = event.location or "Unknown location"
                    # Process the location to extract city and state if applicable
                    formatted_location = extract_city_state(location)
                    # Build the event label with sub-bullet for event name
                    event_label = f"{formatted_location}\n  - {event.name}"
                    event.custom_label = event_label
                    events_by_trainer[trainer_name].append(event)
    
    return events_by_trainer, days  # Return events categorized by trainer

# Function to group events by day
def group_events_by_day(events_by_trainer):
    events_by_day = defaultdict(list)
    today = datetime.now()

    # Organize events by day, across all trainers
    for trainer, event_list in events_by_trainer.items():
        for event in event_list:
            event_day = event.begin.date()
            # Append event and trainer name as tuple
            events_by_day[event_day].append((trainer, event))

    return events_by_day

async def get_page(events_by_trainer, day_index: int, page_index: int = 1):
    today = datetime.now()
    events_by_day = group_events_by_day(events_by_trainer)
    day_key = today + timedelta(days=day_index - 1)  # Determine the day based on the index
    day_events = events_by_day.get(day_key.date(), [])  # Get events for that specific day

    # If no events for the day, return an empty embed
    if not day_events:
        return discord.Embed(title=f"No events for {day_key.strftime('%A, %B %d')}"), 1

    # Split the day's events into chunks of MAX_EMBED_FIELDS (25 fields per embed)
    total_pages_for_day = (len(day_events) - 1) // MAX_EMBED_FIELDS + 1  # Calculate total pages for the day

    # Determine the events for the current page
    start_index = (page_index - 1) * MAX_EMBED_FIELDS
    end_index = start_index + MAX_EMBED_FIELDS
    page_events = day_events[start_index:end_index]  # Get the events for the current page

    # Create the embed for the current page
    embed = discord.Embed(
        title=f"Events for {day_key.strftime('%A, %B %d')}",
        description=f"List of events for {day_key.strftime('%A, %B %d')}",
        color=discord.Color.blue()
    )

    # Add fields to the embed
    for trainer, event in page_events:
        event_description = f"{event.custom_label} (Starts: {event.begin.format('HH:mm')}, Ends: {event.end.format('HH:mm')})"
        event_description = event_description[:MAX_FIELD_LENGTH]  # Ensure within field length limit
        embed.add_field(name=trainer, value=event_description, inline=False)

    # Return the correct page embed and the total number of pages for the day
    return embed, total_pages_for_day


# Function to create an embed for Discord with a table-like format
def create_embed(events_by_trainer, period: str):
    embed = discord.Embed(
        title=f"Upcoming Events for the {period.capitalize()}",
        description=f"Here are the calendar events for the next {period}.",
        color=discord.Color.blue()
    )

    # Group events by day across all trainers
    events_by_day = defaultdict(list)
    today = datetime.now()

    # Organize events by day, across all trainers
    for trainer, event_list in events_by_trainer.items():
        for event in event_list:
            event_day = event.begin.date()
            # Append event and trainer name as tuple
            events_by_day[event_day].append((trainer, event))
    print(events_by_day)

    # Generate the table-like structure
    for i in range(7):  # Assuming 7 days in the period
        day = today + timedelta(days=i)
        day_str = day.strftime('%A, %B %d')  # Format day as "Monday, September 25"
        
        # Get events for the current day
        day_events = events_by_day.get(day.date(), [])

        if day_events:
            events_list = "\n".join(
                f"- {trainer}: {event.custom_label} (Starts: {event.begin.format('HH:mm')}, Ends: {event.end.format('HH:mm')})"
                for trainer, event in day_events
            )
        else:
            events_list = "No events."

        # Add the day's events as a field in the embed
        embed.add_field(name=day_str, value=events_list, inline=False)
        print(events_list)

    return embed



# Function to handle the daily task
async def send_calendar_updates(channel):
    events = []
    links = get_calendar_links()
    for link in links:
        events.extend(get_events_for_next_week(link))
    if events:
        embed = create_embed(events, "week")
        await channel.send(embed=embed)

# Schedule the task at 5 PM EST every day
def schedule_daily_task(client, channel_id):
    est = pytz.timezone('US/Eastern')
    now = datetime.now(est)
    target_time = now.replace(hour=17, minute=0, second=0, microsecond=0)
    if now > target_time:
        target_time += timedelta(days=1)

    def run_scheduled_task():
        scheduler.every().day.at("17:00").do(lambda: client.loop.create_task(send_calendar_updates(client.get_channel(channel_id))))

    return run_scheduled_task
