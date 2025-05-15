import logging
import os
import traceback

import discord
import requests
from discord.ext import tasks

import text_chat
import voice_chat

STATE_CLOSED = 'closed'
STATE_OPEN = 'open'
STATE_UNKNOWN = 'unknown'
ENABLED_STATE_FILE = 'enabled.txt'

discord_token = os.getenv('DISCORD_TOKEN')
space_endpoint = os.getenv('SPACE_ENDPOINT')
channel_id = int(os.getenv('DISCORD_CHANNEL_ID'))

avatars = {}
usernames = {STATE_CLOSED: '🔴 Closed', STATE_OPEN: '🟢 Open', STATE_UNKNOWN: '❓ Unknown'}
people_indicator = '🧙'

current_state = None
current_persons = None
avatar_update_pending = False
is_bot_enabled = True

reconnect_task = None

# Logging configuration
logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


async def update_presence(state, persons):
    global current_state, current_persons, avatar_update_pending

    if state == current_state and persons == current_persons and not avatar_update_pending:
        logging.info(f'No change detected. Skipping update. Current state: {state}, persons: {persons}')
        return

    logging.info(f'Updating the presence to "{state}, {persons}", enabled: {is_bot_enabled}')

    if not client.user:
        logging.error("client.user is null, can't update state")
        return

    nick = (
        f'{usernames[state]} ({persons} {people_indicator})'
        if state == STATE_OPEN and persons is not None
        else usernames[state]
    )

    for guild in client.guilds:
        member = guild.get_member(client.user.id)
        if member and member.nick != nick:
            try:
                await member.edit(nick=nick)
            except Exception as e:
                logging.error(f'Failed to update nickname: {e}')

    if state != current_state or avatar_update_pending:
        try:
            await client.user.edit(avatar=avatars[state])
            avatar_update_pending = False
        except Exception as e:
            logging.error(f'Failed to update avatar to [{state}]: {e}')
            avatar_update_pending = True

    current_state = state
    current_persons = persons


@tasks.loop(minutes=1)
async def is_there_life_on_mars():
    logging.info('Checking the status...')
    try:
        response = requests.get(space_endpoint, timeout=10)
        spaceapi_json = response.json()

        match (is_bot_enabled, spaceapi_json['state']['open']):
            case (False, _):
                space_state = STATE_UNKNOWN
            case (True, True):
                space_state = STATE_OPEN
            case (True, False):
                space_state = STATE_CLOSED

        people = 0
        try:
            if (
                'sensors' in spaceapi_json
                and 'people_now_present' in spaceapi_json['sensors']
                and spaceapi_json['sensors']['people_now_present']
                and isinstance(spaceapi_json['sensors']['people_now_present'], list)
            ):
                people_data = spaceapi_json['sensors']['people_now_present'][0]

                if people_data and 'value' in people_data and people_data['value'] is not None:
                    people_value = people_data['value']
                    if isinstance(people_value, str):
                        people = int(float(people_value))
                    else:
                        people = int(people_value)

            logging.info(f'Current status: {space_state} ({people} in da haus)')
            await update_presence(space_state, people)

        except (TypeError, ValueError, IndexError) as e:
            logging.warning(f'Failed to parse people_now_present value: {e}')
            await update_presence(space_state, people)

    except Exception as e:
        logging.error(f'Error fetching or processing space status: {e}')
        logging.debug(traceback.format_exc())


async def set_enabled_state(enabled: bool):
    global is_bot_enabled

    if is_bot_enabled == enabled:
        return

    is_bot_enabled = enabled
    with open(ENABLED_STATE_FILE, 'w') as f:
        f.write('1' if is_bot_enabled else '0')

    logging.info(f'Set enabled state to: {is_bot_enabled}')
    await is_there_life_on_mars()


def load_enabled_state():
    global is_bot_enabled

    try:
        with open(ENABLED_STATE_FILE, 'r') as f:
            is_bot_enabled = f.read().strip() == '1'
    except FileNotFoundError:
        is_bot_enabled = True
    except Exception as e:
        logging.error(f'Could not read state file: {e}')


def load_avatars():
    for state in usernames:
        with open(f'res/glider_{state}.png', 'rb') as avatar:
            avatars[state] = avatar.read()


@client.event
async def on_ready():
    logging.info(f'Using endpoint: {space_endpoint}')
    for guild in client.guilds:
        logging.info(f'{client.user} has connected to Discord server {guild}!')

    try:
        load_enabled_state()
        load_avatars()

        await client.user.edit(username='glider')
        await client.change_presence(activity=discord.Activity(name='the Space', type=discord.ActivityType.watching))

        is_there_life_on_mars.start()

        voice_chat.init_voice(client, channel_id)
        text_chat.init_chat(client, channel_id, set_enabled_state)

    except Exception:
        logging.error(f'Error during initialization: {traceback.format_exc()}')


client.run(discord_token)
