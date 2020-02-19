import discord
import logging
import asyncio
import os
import json
import time

from discord.ext import commands
from threading import Thread

import s3
import podcast_utils

recording_filename = ""


class ShowCog(commands.Cog):



    def __init__(self, bot, helper, configs):
        self.bot = bot
        self.helper = helper
        self.configs = configs


    
    def start_recordiing(self,show_channel):
        global recording_filename
        recording_filename = show_channel.name + "-" +time.strftime("%Y%m%d-%H%M%S")+ ".wav" 
        self.bot.voice_clients[0].listen(discord.WaveSink(recording_filename))
        return   
    
    @commands.command(name='startshow')
    @commands.has_role('podcast-host')
    async def start_show(self,ctx):
        logging.info("Command '%s' detected in call screening channel (%s).", ctx.command.name, self.configs['CHANNELS']['SCREENING']['name'])
        await self.helper.serverCheck()
        perms = discord.PermissionOverwrite(
            connect=True,
            speak=False,
            mute_members=False,
            deafen_members=False,
            move_members=False,
            use_voice_activation=False,
            priority_speaker=False,
            read_messages=True
        )
        await self.bot.get_channel(self.configs['CHANNELS']['VOICE']['id']).set_permissions(ctx.guild.default_role, overwrite=perms)
        await self.bot.get_channel(self.configs['CHANNELS']['VOICE']['id']).connect()
        self.start_recordiing(self.bot.get_channel(self.configs['CHANNELS']['VOICE']['id']))


    @commands.command(name='endshow')
    @commands.has_role('podcast-host')
    async def end_show(self, ctx):
        logging.info("Command '%s' detected in call screening channel (%s).", ctx.command.name, self.configs['CHANNELS']['SCREENING']['name'])
        perms = discord.PermissionOverwrite(
            connect=False,
            speak=False,
            mute_members=False,
            deafen_members=False,
            move_members=False,
            use_voice_activation=False,
            priority_speaker=False,
            read_messages=False
        )
        await self.bot.get_channel(self.configs['CHANNELS']['VOICE']['id']).set_permissions(ctx.guild.default_role, overwrite=perms)
        await self.helper.clean_livecallers(ctx)
        if self.bot.voice_clients:
            for vc in self.bot.voice_clients:
                vc.stop_listening()
                await vc.disconnect()
            global recording_filename
            s3.save_recording_to_bucket("discord-recordings-dev", recording_filename)

def setup(bot):
    bot.add_cog(ShowCog(bot))