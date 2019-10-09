import logging
import asyncio
import discord

import role_utils
import channel_utils

class show_helper:

    def __init__(self, bot, configs):
        self.bot = bot
        self.configs = configs


    def name(self, member):
        # A helper function to return the member's display name
        nick = name = None
        try:
            nick = member.nick
        except AttributeError:
            pass

        try:
            name = member.name
        except AttributeError:
            pass

        if nick:
            return nick
        if name:
            return name
        return None

    async def is_live_show_happening(self, ctx):
        show_channel = self.bot.get_channel(self.configs['CHANNELS']['VOICE']['id'])
        members = show_channel.members
        member_ids = [member.id for member in members]

        # Check if at least one host is in the live channel
        hosts_in_channel = [host for host in self.configs['HOSTS'] if host in member_ids]
        if len(hosts_in_channel) > 0:
            return True
        else:
            nonlive_channel = self.bot.get_channel(self.configs['CHANNELS']['NONLIVE']['id'])
            nonlive_msg = f'{ctx.author.mention} There is currently no live show. Please post your question in {nonlive_channel.mention} for the next show!'
            await ctx.send(nonlive_msg)
            return False
    
    def is_anyone_mentioned(self, ctx):
        try:
            mentioned_user = ctx.message.mentions[0]
        except:
            mentioned_user = None
        return mentioned_user

    async def clean_and_add_livecallers(self, ctx, user=None):
        # Clean Live Callers of any stale users
        live_caller_role = discord.utils.find(lambda m: m.id == self.configs['ROLES']['CALLER']['id'], ctx.guild.roles)
        logging.info('Found Live Caller Role - %s', live_caller_role)
        for member in live_caller_role.members:
            if member != user:
                msg_extra_live = f'FYI - I discovered that {member.name} was still in the Live Callers group while trying to add a new user. I have removed them now.'
                await ctx.send(msg_extra_live)
                await member.remove_roles(live_caller_role)

        # Add Requested User to Live Caller Role
        await user.add_roles(live_caller_role)
    
    async def clean_livecallers(self, ctx):
        # Clean Live Callers of any stale users
        live_caller_role = discord.utils.find(lambda m: m.id == self.configs['ROLES']['CALLER']['id'], ctx.guild.roles)
        logging.info('Found Live Caller Role - %s', live_caller_role)
        for member in live_caller_role.members:
            await member.remove_roles(live_caller_role)

    async def gather_caller_info(self, author):
        # Implement wait_for check (is author & DM)
        def check(m):
            return m.author == author and isinstance(m.channel, discord.DMChannel)

        await author.send("Thanks for wanting to call in. Before we get you on the line, let's get a few details.")

        # Ask Question 1
        await author.send("What should we call you?")
        caller_name = await self.bot.wait_for('message', timeout=30, check=check)
        caller_name = caller_name.content

        # Ask Question 2
        await author.send(f'Hey {caller_name} - where are you from?')
        caller_location = await self.bot.wait_for('message', timeout=30, check=check)
        caller_location = caller_location.content

        # Ask Question 3
        await author.send(f'Thanks for that {caller_name} - what would you like to discuss?')
        caller_topic = await self.bot.wait_for('message', timeout=30, check=check)
        caller_topic = caller_topic.content

        # Send confirmation message
        caller_details = f'{caller_name} from {caller_location} wants to talk about - {caller_topic}'
        await author.send(f'We will send the following message to the live show screening channel.\n'
                        f'`{caller_details}`\n\nIf this is correct, reply with the word YES.')
        caller_confirm = await self.bot.wait_for('message', timeout=30, check=check)

        if 'YES' in caller_confirm.content.upper():
            e = discord.Embed(title='NEW CALLER ALERT!', description=caller_details)
            # e.set_thumbnail(url=author.avatar_url)
            e.add_field(name='\a', value='\a', inline=False)  # Blank line (empty field)
            e.add_field(name='To add the caller:', value=f"!{self.configs['COMMANDS']['answer']} {author.mention}", inline=False)
            e.add_field(name='To remove the caller:', value=f"!{self.configs['COMMANDS']['hangup']}", inline=False)

            screening_channel = self.bot.get_channel(self.configs['CHANNELS']['SCREENING']['id'])
            await screening_channel.send(embed=e)
            await author.send('Awesome - thanks! Your message has been sent '
                            'and you will be notified when you are dialed into the live show!')

    async def serverCheck(self):
        logging.info('Setting up server')
        await role_utils.role_check(self.bot)
        await channel_utils.channel_check(self.bot)
        logging.info('Server setup complete')    
        return