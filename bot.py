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


async def update_presence(state, persons):
    global current_state, current_persons

    # Only proceed if there's an actual change
    if state != current_state or persons != current_persons:
        logging.info(f'Updating the presence to "{state}, {persons}"')

        if client.user:
            nick = (
                f'{usernames[state]} ({persons} {people_indicator})'
                if state == 'open' and persons is not None
                else usernames[state]
            )

            # Get lock emoji and formatted channel name
            lock_icon = '🔴🔒' if state == 'closed' else '🟢🔓'
            channel_state = 'closed' if state == 'closed' else f"open-{persons or '?'}"
            formatted_channel_name = f'{lock_icon}-{channel_name}-{channel_state}'

            for guild in client.guilds:
                member = guild.get_member(client.user.id)
                if member:
                    await member.edit(nick=nick)

                channel = guild.get_channel(int(channel_id))
                if channel:
                    await channel.edit(name=formatted_channel_name)
                else:
                    logging.warning(f'Channel {channel_id} not found')

            if state != current_state:
                try:
                    await client.user.edit(avatar=avatars[state])
                except Exception as e:
                    logging.error(f'Failed to update avatar {state}: {e}')

        # After successful update, store the new state
        current_state = state
        current_persons = persons


# Fire every minute
@tasks.loop(minutes=1)
async def is_there_life_on_mars():
    logging.info('Checking the status')
    try:
        response = requests.get(space_endpoint, timeout=10)
        spaceapi_json = response.json()
        space_state = 'open' if spaceapi_json['state']['open'] else 'closed'
        try:
            people = spaceapi_json['sensors']['people_now_present'][0].get('value', 0)
            if isinstance(people, str):
                people = int(float(people))
            else:
                people = int(people)
        except (TypeError, ValueError, IndexError) as e:
            logging.warning(f'Failed to parse people_now_present value: {e}')
            people = 0

        logging.info(f'Current status: {space_state} ({people} in da haus)')
        await update_presence(space_state, people)

    except Exception as e:
        logging.error(f"Error fetching or processing space status: {e}")


@client.event
async def on_ready():
    for guild in client.guilds:
        logging.info(f'{client.user} has connected to Discord server {guild} using endpoint {space_endpoint}!')

    try:
        for state in ['closed', 'open']:
            with open(f'res/glider_{state}.png', 'rb') as avatar:
                avatars[state] = avatar.read()

        await client.user.edit(username='glider')
        await client.change_presence(activity=discord.Activity(name='the Space', type=discord.ActivityType.watching))

        is_there_life_on_mars.start()
    except Exception as e:
        logging.error(f"Error during initialization: {traceback.format_exc()}")

client.run(discord_token)
