import asyncio
import logging

import discord
import discord.voice_client as vc
from discord.ext import tasks

# Force NaCl check to True
# Our bot doesn't use actual audio and won't ever need it
# This saves us from having to build it all (takes 20 extra min in the pipe)
vc.has_nacl = True

channel_id = None
client: discord.Client = None
reconnect_task = None


def init_voice(client_instance: discord.Client, voice_channel_id: int):
    global client, channel_id
    client = client_instance
    channel_id = voice_channel_id

    client.event(on_voice_state_update)
    ensure_bot_in_voice.start()


@tasks.loop(minutes=1)
async def ensure_bot_in_voice():
    connected = any(vc.channel and vc.channel.id == channel_id for vc in client.voice_clients)
    if not connected and (not reconnect_task or reconnect_task.done()):
        logging.warning('Bot is not in the correct voice channel. Rejoining...')
        await join_voice_channel()


async def on_voice_state_update(member, before, after):
    global reconnect_task

    if member.id != client.user.id:
        return

    logging.info(
        f'Channel changed: {before.channel.id if before.channel else 0} -> {after.channel.id if after.channel else 0}'
    )

    if after.channel is None or after.channel.id != channel_id:
        if reconnect_task is None or reconnect_task.done():
            reconnect_task = asyncio.create_task(delayed_reconnect())


async def delayed_reconnect():
    logging.info('Bot moved or disconnected — scheduling reconnect...')
    await asyncio.sleep(3)
    await join_voice_channel()


async def join_voice_channel():
    channel = client.get_channel(channel_id) or await client.fetch_channel(channel_id)

    if not isinstance(channel, discord.VoiceChannel):
        logging.error(f'Channel {channel_id} is not a voice channel')
        return

    voice_client = channel.guild.voice_client
    if voice_client:
        if voice_client.channel.id == channel_id:
            logging.info('Already connected to desired channel')
            return
        await voice_client.disconnect(force=True)

    logging.info(f'Connecting to voice channel {channel_id}...')
    await channel.connect(reconnect=True, self_deaf=True, self_mute=True)
    logging.info(f'Connected to voice channel {channel_id}!')
