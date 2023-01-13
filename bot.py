import logging
import os
import socket
import traceback
import json

import aiocron
import discord
from dotenv import load_dotenv
import requests

load_dotenv()
discord_token = os.getenv('DISCORD_TOKEN')
space_edpoint = os.getenv('SPACE_ENDPOINT')

avatars = {}

COUNTER_INFO = (os.getenv('COUNTER_HOST', "counter.local"), 26178)
usernames = {
    'closed': 'Space zamknięty',
    'open': 'Space otwarty'
}

online_status = {
    'closed': discord.Status.offline,
    'open': discord.Status.online
}

current_state = None

# Logging configuration
logging.basicConfig(level=logging.INFO)

client = discord.Client()

async def update_state(state):
    if client.user:
        logging.info(f'Updating the presence to "{state}"')
        await client.change_presence(activity=discord.Activity(name=f"the Space (*{state}*)", type=discord.ActivityType.watching))
        try:
            await client.user.edit(avatar=avatars[state])
        except:
            logging.exception(traceback.format_exc())
        for guild in client.guilds:
            member = guild.get_member_named(client.user.name)
            if state == "open":
                try:
                    logging.info(f'Asking The Count how many hackers are there')
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                        sock.connect(COUNTER_INFO)
                        counts = json.loads(sock.recv(1024).decode("UTF-8"))
                        logging.info(counts)
                        persons = counts["persons"]
                        logging.info(f'The Count says there are {persons} people')
                except BaseException:
                    logging.exception(traceback.format_exc())
                    await member.edit(nick=usernames[state])
                else:
                    await member.edit(nick=usernames[state] + f" - {persons} people in da haus")
            else:
                await member.edit(nick=usernames[state])


async def update_presence(state):
    global current_state
    if state != current_state:
        current_state = state
        await update_state(state)

# Fire every minute
@aiocron.crontab('* * * * *')
async def is_there_life_on_mars():
    logging.info('Checking the status')
    space_state = requests.get(space_edpoint).json()['state']['open']
    if space_state:
        space_state = 'open'
    else:
        space_state = 'closed'
    logging.info(f'Current status: {space_state}')
    await update_presence(space_state)

@client.event
async def on_ready():
    for guild in client.guilds:
        logging.info(f'{client.user} has connected to Discord server {guild} using endpoint {space_edpoint}!')
    for state in ['closed', 'open']:
        with open(f'res/glider_{state}.png', 'rb') as avatar:
            avatars[state] = avatar.read()
    try:
        await client.user.edit(username='glider')
    except:
        logging.error(traceback.format_exc())
    await update_presence('closed')

client.run(discord_token)
