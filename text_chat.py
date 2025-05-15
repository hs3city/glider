import logging

import discord

client = None
channel_id = None
set_enabled_state = None


def init_chat(client_instance, voice_channel_id: int, set_enabled_state_fn):
    global client, channel_id, set_enabled_state
    client = client_instance
    channel_id = int(voice_channel_id)
    set_enabled_state = set_enabled_state_fn

    client.event(on_message)


async def on_message(message):
    if message.author == client.user:
        return

    if message.channel.id != channel_id:
        return

    cmd = message.content.strip().lower()
    if cmd == '!glider off':
        await set_enabled_state(False)
    elif cmd == '!glider on':
        await set_enabled_state(True)
    elif cmd == '!help':
        await post_help_message(message)


async def post_help_message(message):
    embed = discord.Embed(
        title='🪂 Glider sees you', description='Here are the available commands:', color=discord.Color.blurple()
    )
    embed.add_field(name='`!glider off`', value='Disables status updates and sets status to `Unknown`', inline=False)
    embed.add_field(name='`!glider on`', value='Re-enables status updates from the space API', inline=False)
    embed.add_field(name='`!help`', value='Guess what?', inline=False)

    await message.channel.send(embed=embed)
