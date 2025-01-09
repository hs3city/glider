import logging
import os
import traceback

import discord
import requests
from discord.ext import tasks

discord_token = os.getenv('DISCORD_TOKEN')
space_endpoint = os.getenv('SPACE_ENDPOINT')
channel_id = os.getenv('DISCORD_CHANNEL_ID')

avatars = {}
usernames = {'closed': 'Closed', 'open': 'Open'}

online_status = {'closed': discord.Status.offline, 'open': discord.Status.online}

people_indicator = '🧙'
channel_name = 'space-is'

current_state = None
current_persons = None

# Logging configuration
logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
client = discord.Client(intents=intents)


async def update_state(state, persons):
    if client.user:
        logging.info(f'Updating the presence to "{state}, {persons}"')
        nick = (
            f'{usernames[state]} ({persons} {people_indicator})'
            if state == 'open' and persons is not None
            else usernames[state]
        )
        for guild in client.guilds:
            member = guild.get_member_named(client.user.name)
            await member.edit(nick=nick)

            # Getting channel ID and setting status for it
            channel = guild.get_channel(int(channel_id))
            if channel:
                # Setting lock emoji and actual status
                lock_icon = '🔴🔒' if state == 'closed' else '🟢🔓'
                channel_state = 'closed' if state == 'closed' else f"open-{persons or '?'}"
                formatted_channel_name = f'{lock_icon}-{channel_name}-{channel_state}'

                # Setting actual status
                await channel.edit(name=formatted_channel_name)
            else:
                logging.warning(f'Channel {channel_id} not found')


async def update_presence(state, persons):
    global current_state, current_persons

    if state != current_state or persons != current_persons:
        await update_state(state, persons)
        current_state = state
        current_persons = persons


# Fire every minute
@tasks.loop(minutes=1)
async def is_there_life_on_mars():
    logging.info('Checking the status')
    spaceapi_json = requests.get(space_endpoint).json()
    if spaceapi_json['state']['open']:
        space_state = 'open'
    else:
        space_state = 'closed'
    people = int(spaceapi_json['sensors']['people_now_present'][0]['value'])
    logging.info(f'Current status: {space_state} ({people} in da haus)')
    await update_presence(space_state, people)


@client.event
async def on_ready():
    for guild in client.guilds:
        logging.info(f'{client.user} has connected to Discord server {guild} using endpoint {space_endpoint}!')
    for state in ['closed', 'open']:
        with open(f'res/glider_{state}.png', 'rb') as avatar:
            avatars[state] = avatar.read()
    try:
        await client.user.edit(username='glider')
        await client.user.edit(avatar=avatars['open'])
        await client.change_presence(activity=discord.Activity(name='the Space', type=discord.ActivityType.watching))
    except:
        logging.error(traceback.format_exc())
    is_there_life_on_mars.start()


client.run(discord_token)
