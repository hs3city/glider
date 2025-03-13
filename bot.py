import logging
import os
import traceback
import time
from datetime import datetime, timedelta

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

confirmation_needed = False
confirmation_start_time = None
# Wait 3 minutes before confirming closed state
confirmation_delay_minutes = 3
pending_state = None

# Logging configuration
logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
client = discord.Client(intents=intents)


async def update_channel_name(channel, formatted_channel_name):
    try:
        await channel.edit(name=formatted_channel_name)
        logging.info(f"Updated channel name to: {formatted_channel_name}")
        return True
    except discord.errors.HTTPException as e:
        if e.status == 429:
            retry_after = e.retry_after
            scope = getattr(e, 'scope', 'unknown')
            bucket = None

            if hasattr(e, 'response') and hasattr(e.response, 'headers'):
                headers = e.response.headers
                bucket = headers.get('X-RateLimit-Bucket')

                logging.warning(
                    f"Rate limited when updating channel name. "
                    f"Scope: {scope}, Retry after: {retry_after}s, "
                    f"Bucket: {bucket}"
                )
            else:
                logging.warning(f"Rate limited when updating channel name. Retry after: {retry_after}s")

            return False
        else:
            logging.error(f"Failed to update channel: {e}")
            return False


async def update_presence(state, persons):
    global current_state, current_persons, confirmation_needed, confirmation_start_time, pending_state

    if current_state == 'open' and state == 'closed' and not confirmation_needed:
        logging.info(
            f"Space appears to be closing. Starting confirmation timer of {confirmation_delay_minutes} minutes.")
        confirmation_needed = True
        confirmation_start_time = datetime.now()
        pending_state = 'closed'
        return

    if confirmation_needed and state == 'open':
        logging.info("Space is open again. Cancelling close confirmation.")
        confirmation_needed = False
        pending_state = None

    if state == current_state and persons == current_persons and not confirmation_needed:
        logging.info(f"No change detected. Skipping update. Current state: {state}, persons: {persons}")
        return

    logging.info(f'Updating the presence to "{state}, {persons}"')

    if client.user:
        nick = (
            f'{usernames[state]} ({persons} {people_indicator})'
            if state == 'open' and persons is not None
            else usernames[state]
        )

        lock_icon = '🔴🔒' if state == 'closed' else '🟢🔓'
        channel_state = 'closed' if state == 'closed' else 'open'
        formatted_channel_name = f'{lock_icon}-{channel_name}-{channel_state}'

        for guild in client.guilds:
            member = guild.get_member(client.user.id)
            if member:
                try:
                    await member.edit(nick=nick)
                except Exception as e:
                    logging.error(f"Failed to update nickname: {e}")

            channel = guild.get_channel(int(channel_id))
            if channel and (state != current_state or confirmation_needed):
                success = await update_channel_name(channel, formatted_channel_name)
                if not success:
                    logging.info("Not updating state tracking due to failed channel update")
                    return
            else:
                if not channel:
                    logging.warning(f'Channel {channel_id} not found')

        if state != current_state:
            try:
                await client.user.edit(avatar=avatars[state])
            except Exception as e:
                logging.error(f'Failed to update avatar {state}: {e}')

    current_state = state
    current_persons = persons

    if confirmation_needed and state == 'closed':
        confirmation_needed = False
        pending_state = None


# Fire every minute
@tasks.loop(minutes=1)
async def is_there_life_on_mars():
    global confirmation_needed, confirmation_start_time, pending_state

    if confirmation_needed:
        time_elapsed = datetime.now() - confirmation_start_time
        if time_elapsed >= timedelta(minutes=confirmation_delay_minutes):
            logging.info(f"Confirmation period elapsed. Checking if space is still {pending_state}.")
        else:
            minutes_left = confirmation_delay_minutes - time_elapsed.total_seconds() / 60
            logging.info(f"In confirmation period for {pending_state} state. {minutes_left:.1f} minutes left.")

    logging.info('Checking the status')
    try:
        response = requests.get(space_endpoint, timeout=10)
        spaceapi_json = response.json()
        space_state = 'open' if spaceapi_json['state']['open'] else 'closed'
        people = 0
        try:
            if ('sensors' in spaceapi_json and
                    'people_now_present' in spaceapi_json['sensors'] and
                    spaceapi_json['sensors']['people_now_present'] and
                    isinstance(spaceapi_json['sensors']['people_now_present'], list)):

                people_data = spaceapi_json['sensors']['people_now_present'][0]

                if people_data and 'value' in people_data and people_data['value'] is not None:
                    people_value = people_data['value']
                    if isinstance(people_value, str):
                        people = int(float(people_value))
                    else:
                        people = int(people_value)

            logging.info(f'Current status: {space_state} ({people} in da haus)')

            if confirmation_needed and space_state == pending_state:
                time_elapsed = datetime.now() - confirmation_start_time
                if time_elapsed >= timedelta(minutes=confirmation_delay_minutes):
                    logging.info(f"Confirmation period elapsed. Status remained {pending_state}. Updating now.")
                    await update_presence(space_state, people)
            else:
                await update_presence(space_state, people)

        except (TypeError, ValueError, IndexError) as e:
            logging.warning(f'Failed to parse people_now_present value: {e}')
            await update_presence(space_state, people)

    except Exception as e:
        logging.error(f"Error fetching or processing space status: {e}")
        logging.debug(traceback.format_exc())


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