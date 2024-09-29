import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import schedule_handler as schedule
from pagination import Pagination

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
GUILD_NAME = os.getenv('DISCORD_GUILD_NAME')
SCHEDULE_CHANNEL_ID = os.getenv('DISCORD_SCHEDULE_CHANNEL_ID')

intents = discord.Intents.all()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    for guild in client.guilds:
        if guild.name == GUILD_NAME:
            break

    await tree.sync(guild=discord.Object(guild.id))

    print(
        f'{client.user} is connected to the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )

    schedule.schedule_daily_task(client, SCHEDULE_CHANNEL_ID)()

# Slash command to add a calendar link
@tree.command(name="add-cal", description="Add an iCal calendar link.", guild=discord.Object(GUILD))
async def add_cal(interaction: discord.Interaction, link: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You need to be an administrator to add a calendar link.")
        return
    
    try:
        # Normalize the link to avoid duplicates
        normalized_link = normalize_link(link)

        # Get all current calendar links and normalize them
        current_links = [normalize_link(existing_link) for existing_link in schedule.get_calendar_links()]

        # Check if the link already exists
        if normalized_link in current_links:
            await interaction.response.send_message(f"The calendar link `{link}` already exists.", ephemeral=True)
            return

        # Store the new calendar link
        schedule.store_calendar_link(link)
        await interaction.response.send_message(f"Calendar link `{link}` added!")
    except Exception as e:
        await interaction.response.send_message(f"Please provide a valid calendar link.")
        return

# Helper function to fetch events for a specific period
async def fetch_and_display_events(interaction: discord.Interaction, period: str):
    try:
        events, days = await schedule.get_calendar_events(period)
        if not events:
            await interaction.response.send_message(f"No events found for the {period}.")
            return
        
        # events_by_day = schedule.group_events_by_day(events)
        pagination_view = Pagination(interaction, schedule.get_page, total_days=days, events=events)
        await pagination_view.navigate()
    except Exception as e:
        await interaction.response.send_message(f"An error occurred while fetching events: {e}")

# Slash command to view calendar events for the day
@tree.command(name="view-cal-day", description="View today's calendar events.", guild=discord.Object(id=GUILD))
async def view_cal_day(interaction: discord.Interaction):
    await fetch_and_display_events(interaction, "day")

# Slash command to view calendar events for the week
@tree.command(name="view-cal-week", description="View this week's calendar events.", guild=discord.Object(id=GUILD))
async def view_cal_week(interaction: discord.Interaction):
    await fetch_and_display_events(interaction, "week")

# Slash command to view calendar events for the month
@tree.command(name="view-cal-month", description="View this month's calendar events.", guild=discord.Object(id=GUILD))
async def view_cal_month(interaction: discord.Interaction):
    await fetch_and_display_events(interaction, "month")

client.run(TOKEN)