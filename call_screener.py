import logging

import discord
from discord.ext import commands
from discord.ext.commands import Bot

BOT_PREFIX = ("?", "!")

class CallScreenerBot:

    def __init__(self, token, call_in_channel, screening_channel):
        logging.basicConfig(
            # filename=debug_file_name,
            level=logging.INFO,
            format='%(asctime)s %(module)s %(msg)s',
        )
        logging.info("[*] Initializing bot...")
        # with open(token_file_name) as token_file:
        #     self.token = token_file.read().strip()
        self.token = token
        self.call_in_channel = call_in_channel
        self.screening_channel = screening_channel
        self.client = Bot(command_prefix=BOT_PREFIX)
        self.setup()


    def get_channel(self, channels, channel_name):
        for channel in self.client.get_all_channels():
            if channel.name == channel_name:
                return channel
        return None


    def run(self):
        logging.info("[*] Running...")
        self.client.run(self.token)


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


    # Clears all Live Callers (ensures only 1 user has this role)
    def get_live_callers(self, context, user_to_add):
        extra_live_callers = list()
        all_members = context.message.server.members
        for member in all_members:
            if member != user_to_add and 'Live Caller' in ", ".join([role.name for role in member.roles]):
                extra_live_callers.append(member)
                logging.info('Extra Live Caller: ' + self.name(member))

        return extra_live_callers


    def setup(self):
        @self.client.event
        async def on_ready():
            logging.info("[+] Connected as " + self.client.user.name)
            logging.info("[+] Listening for private messages and in channel #" + self.call_in_channel)
            await self.client.change_presence(game=discord.Game(name='Screening Calls'))

        @self.client.event
        async def on_message(message):
            # Ignore messages by bots (including self)
            if message.author.bot:
                return

            # Only return help in designated channel
            if message.content.startswith(BOT_PREFIX):
                msg = message.content.strip("".join(list(BOT_PREFIX)))
                if msg.startswith("help"):
                    if not message.channel.is_private and message.channel.name != self.call_in_channel:
                        return

            # Pass on to rest of the client commands
            if message.content.startswith(BOT_PREFIX):
                await self.client.process_commands(message)

        @self.client.event
        async def on_command_error(error, context):
            if isinstance(error, commands.CommandOnCooldown):
                msg_cooldown = f"This command can only be sent every 30 seconds. Please reply to the questions above to dial-in."
                await self.client.send_message(context.message.author, content=msg_cooldown)
                # await self.client.send_message(context.message.author, content='This command is on a %.2fs cooldown' % error.retry_after)
            raise error  # re-raise the error so all the errors will still show up in console



        # Monitor Voice Channel for Joins
        # Notify when a Live Caller Joins
        @self.client.event
        async def on_voice_state_update(before, after):
            if before.voice.voice_channel is None and after.voice.voice_channel is not None:
                logging.info('Member Joined: ' + self.name(before))

                for role in before.roles:
                    if role.name == 'Live Caller':
                        msg_user_voice = f'{self.name(before)} has now joined the Live Show voice channel!'
                        await self.client.send_message(self.get_channel(self.client.get_all_channels, self.screening_channel), msg_user_voice)


        @self.client.command(description="Adds a user to the active voice channel (to call in).",
                             brief="Patch them through.",
                             pass_context=True)
        # @discord.ext.commands.has_role("Admin")
        async def answer(context):
            if context.message.channel.name != self.screening_channel:
                return

            logging.info('Answer command accepted in screening channel.')
            # user_to_add = context.message.content.strip("".join(list(BOT_PREFIX))).replace("answer", "").strip()
            try:
                user_to_add = context.message.mentions[0]
                logging.info('User to Add: ' + self.name(user_to_add))
            except:
                logging.warning('No users mentioned - invalid command.')
                return

            # Clearing Extra Live Callers (when !hangup not used)
            live_caller_role = discord.utils.get(user_to_add.server.roles, name="Live Caller")
            extra_live_callers = self.get_live_callers(context, user_to_add)
            for live_caller in extra_live_callers:
                await self.client.remove_roles(live_caller, live_caller_role)
                msg_extra_live = f'FYI - I discovered that {self.name(live_caller)} was still in the Live Callers group while trying to add a new user. I have removed them now.'
                await self.client.send_message(self.get_channel(self.client.get_all_channels, self.screening_channel), msg_extra_live)

            role = discord.utils.get(user_to_add.server.roles, name="Live Caller")
            logging.info('Role to Add To: ' + role.name)
            await self.client.add_roles(user_to_add, role)

            voice_channel = self.client.get_channel('515565007774154766')
            logging.info('Channel to Add To: ' + voice_channel.name)
            await self.client.move_member(user_to_add, voice_channel)

            logging.info('Voice Channel Members - ' + str(voice_channel.voice_members))
            live_show_nicks = list()
            for member in voice_channel.voice_members:
                live_show_nicks.append(member.nick)

            user_in_voice = False
            if user_to_add.nick in live_show_nicks:
                user_in_voice = True

            if user_in_voice:
                add_msg = f'{self.name(user_to_add)} has been added to the Live Caller role and can speak in the voice channel.'
                msg_user_notification = f'You are now connected to the live show!'
            else:
                add_msg = f'{self.name(user_to_add)} has been added to the Live Caller role, but is not yet in the voice channel. I will let you know when they join.'
                msg_user_notification = f'You are now connected to the live show! Please be sure you are connected to the {voice_channel.mention} channel to talk.'

            # Send the Screening notification & User a DM for the live call-in
            await self.client.send_message(self.get_channel(self.client.get_all_channels, self.screening_channel), add_msg)
            await self.client.send_message(user_to_add, msg_user_notification)


        @self.client.command(description="Removes a user from the active voice channel - can still listen.",
                             brief="Hang up!",
                             pass_context=True)
        async def hangup(context):
            if context.message.channel.name != self.screening_channel:
                return

            logging.info('Hangup command accepted in screening channel.')
            # user_to_add = context.message.content.strip("".join(list(BOT_PREFIX))).replace("answer", "").strip()
            try:
                user_to_remove = context.message.mentions[0]
            except:
                logging.warning('No users mentioned - invalid command.')
                return

            logging.info('User to Remove: ' + self.name(user_to_remove))
            role = discord.utils.get(user_to_remove.server.roles, name="Live Caller")
            logging.info('Role to Remove From: ' + role.name)
            await self.client.remove_roles(user_to_remove, role)

            remove_msg = f'{self.name(user_to_remove)} has been removed from the Live Caller role.'
            await self.client.send_message(self.get_channel(self.client.get_all_channels, self.screening_channel), remove_msg)


        # Call-In Command (Active Voice)
        @self.client.command(description="DMs user to get details before calling into the currently live show.",
                             brief="Caller details via DM.",
                             aliases=['CALL'],
                             pass_context=True)
        @commands.cooldown(1, 30, commands.BucketType.user)
        async def call(context):
            # Check if there is a live show
            voice_channel = self.get_channel(self.client.get_all_channels, 'devils-daily-live')
            logging.info('Voice Channel Members - ' + str(voice_channel.voice_members))
            live_show_nicks = list()
            for member in voice_channel.voice_members:
                live_show_nicks.append(member.nick)

            if 'Dave Turner' not in live_show_nicks or 'Jeff O\'Connor' not in live_show_nicks:
                logging.info('There is currently no live show.')
                # questions_channel = self.client.get_channel('517494344794767371')
                # await self.client.say(f'There is currently no live show. Please post your question in {questions_channel.mention} for the next show!')
                # return

            # Only respond to the channel designated and private messages.
            if not context.message.channel.is_private and context.message.channel.name != self.call_in_channel:
                return

            # Checks if the message is a DM.
            def check_isdm(message):
                return message.channel.type == discord.ChannelType.private

            await self.client.send_message(context.message.author, "Thanks for wanting to call in. Before we get you on the line, let's get a few details.")
            await self.client.send_message(context.message.author, "What should we call you?")
            message = await self.client.wait_for_message(timeout=30, author=context.message.author, check=check_isdm)
            if message is None:
                await self.client.send_message(context.message.author, f"We haven't heard from you in a while. If you'd like to call back in, please issue the `!call` command again!")
                return
            msg_caller_name = message.content

            await self.client.send_message(context.message.author, f'Hey {msg_caller_name} - where are you from?')
            message = await self.client.wait_for_message(timeout=30, author=context.message.author, check=check_isdm)
            if message is None:
                await self.client.send_message(context.message.author, f"We haven't heard from you in a while. If you'd like to call back in, please issue the `!call` command again!")
                return
            msg_caller_loc = message.content

            await self.client.send_message(context.message.author, f'Thanks for that {msg_caller_name} - what would you like to discuss?')
            message = await self.client.wait_for_message(timeout=30, author=context.message.author, check=check_isdm)
            if message is None:
                await self.client.send_message(context.message.author, f"We haven't heard from you in a while. If you'd like to call back in, please issue the `!call` command again!")
                return
            msg_caller_topic = message.content

            caller_details = f'{msg_caller_name} from {msg_caller_loc} wants to talk about - {msg_caller_topic}'
            await self.client.send_message(context.message.author, f'We will send the following message to the live show screening channel.\n`{caller_details}`\n\nIf this is correct, reply with the word YES.')
            message = await self.client.wait_for_message(timeout=30, author=context.message.author, check=check_isdm)
            if message is None:
                await self.client.send_message(context.message.author, f"We haven't heard from you in a while. If you'd like to call back in, please issue the `!call` command again!")
                return
            msg_caller_confirm = message.content

            if 'YES' in msg_caller_confirm.upper():
                msg_command_addcaller = (f'NEW CALLER ALERT!\n'
                                         f'{caller_details}\n\n'
                                         f'Type the following command to add the caller:\n'
                                         f'!answer {context.message.author.mention}\n\n'
                                         f'And the following to remove them once the call is over:\n'
                                         f'!hangup {context.message.author.mention}')
                await self.client.send_message(context.message.author, f'Awesome - thanks! Your message has been sent and you will be notified when you are dialed into the live show!')
                await self.client.send_message(self.get_channel(self.client.get_all_channels, 'live-show-screening'), msg_command_addcaller)
