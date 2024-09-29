import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import schedule

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
GUILD_NAME = os.getenv('DISCORD_GUILD_NAME')

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

# Slash command to add a calendar link
@tree.command(name="add-cal", description="Add an iCal calendar link.", guild=discord.Object(GUILD))
async def add_cal(interaction: discord.Interaction, link: str):
    try:
        schedule.store_calendar_link(link)
        await interaction.response.send_message(f"Calendar link `{link}` added!")
    except Exception as e:
        await interaction.response.send_message(f"Please provide a valid calendar link.")
        return


client.run(TOKEN)