import asyncio
import logging

import discord
from configobj import ConfigObj
from validate import Validator

logging.basicConfig(level=logging.INFO)


class Config:
    def __init__(self):
        self.cfgspec = ['[__many__]', '[[__many__]]', 'send_every = integer', 'cooldown = float',
                        'embed = boolean', 'content = multiline']
        self.checks = {
            'multiline': self.multiline
        }

    def load(self):
        cfg = ConfigObj('config.ini', configspec=self.cfgspec, list_values=False)
        cfg.validate(Validator(self.checks))
        return cfg

    def multiline(self, value):
        return value.replace('\\n', '\n')


async def remove_cooldown(msg):
    try:
        await asyncio.sleep(msg['cooldown']*60)
    except asyncio.CancelledError:
        pass
    finally:
        pass
    msg['on_cd'] = False
    print(f'Removed {str(msg)} from cd')


class AdvertisementClient(discord.Client):
    def __init__(self):
        self.cfg = Config().load()
        self.running_cooldowns = []

        super().__init__()

    async def on_ready(self):
        logging.info("Advertisement loaded in {0} servers".format(len(self.guilds)))

    async def close(self):
        await self.clear_messages()
        await super().close()

    async def on_message(self, message: discord.Message):
        if not message.author.bot:
            if message.content == '?adv_reload' and message.author.guild_permissions.administrator:
                await self.clear_messages()
                self.cfg = Config().load()
                await message.channel.send(embed=discord.Embed(color=discord.Colour.green(),
                                                               description='Configurazioni ricaricate'))
            else:
                channel_id = str(message.channel.id)
                if channel_id in self.cfg:
                    for msg_id in self.cfg[channel_id]:
                        msg = self.cfg[channel_id][msg_id]

                        if 'on_cd' in msg and msg['on_cd']:
                            print(f"Message {msg_id} on cooldown")
                            continue

                        if 'count' not in msg:
                            msg['count'] = 1
                        else:
                            msg['count'] += 1

                        if msg['count'] >= msg['send_every']:
                            msg['count'] = 0

                            if 'prev' in msg:
                                try:
                                    await msg['prev'].delete()
                                except discord.errors.NotFound:
                                    pass

                            if msg['cooldown'] > 0:
                                msg['on_cd'] = True
                                self.running_cooldowns.append(asyncio.get_running_loop()
                                                              .create_task(remove_cooldown(msg)))

                            content = msg['content']

                            if msg['embed']:
                                color = getattr(discord.Colour, msg['embed_color'])()
                                embed = discord.Embed(title=msg['embed_title'],
                                                      color=color)
                                embed.description = content
                                msg['prev'] = await message.channel.send(embed=embed)
                            else:
                                msg['prev'] = await message.channel.send(content)

    async def clear_messages(self):
        for task in self.running_cooldowns:
            task.cancel()
        for key in self.cfg:
            if key == 'Token':
                continue
            for msg_id in self.cfg[key]:
                msg = self.cfg[key][msg_id]

                if 'count' in msg:
                    msg['count'] = 0

                if 'prev' in msg:
                    try:
                        await msg['prev'].delete()
                    except discord.errors.NotFound:
                        pass


client = AdvertisementClient()

client.run(client.cfg['Token'])
