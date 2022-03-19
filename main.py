import time
import discord
import os
from discord.ext import commands
from keep_alive import keep_alive
from discord.ext.commands import has_permissions, MissingPermissions
import functions
from threading import Timer
import random
from pymongo import MongoClient
import math
import datetime
# global vars
intents = discord.Intents.all()
believe_pool, doubt_pool, global_dict, guild_member, payout_pool = {}, {}, {}, {}, {}
global posts, cluster
START_COM_DESCRIPTION = "If the title/blv/dbt is more than one word use \"\". t is the time and is in seconds i.e. t = 120 = 2 minutes (Only admins can use)"
GIVE_COM_DESCRIPTION = "Gives points to specific member, you have to type their discord NAME (Only admins can use)."
REFUND_COM_DESCRIPTION = "Refunds points and stops prediction (Only admins can use)."
WON_COM_DESCRIPTION = "Sets win after a prediction has started, side = \"blv\" or \"dbt\" (Only admins can use)."
TOKEN, GUILD, CHANNEL1, CHANNEL2, CHANNEL3 = os.getenv("Token"), os.getenv("Guild"), os.getenv("Channel1"), os.getenv("Channel2"), os.getenv("Channel3")
CLUSTER_LINK, CLUSTER_ELEMENT, DB_ELEMENT = os.getenv("ClusterLink"), os.getenv("PointsData"), os.getenv("UserPoints")
cluster = MongoClient(CLUSTER_LINK)

####################################
# functions that can't be exported #
####################################
'''
lists all the guilds that the bot is in and then checks to see if the guild is a database
if it isn't it gets all members using get_members(new Guild, new collection for new Guild)
only reason why it isn't just one DB is because I was getting dup errors for it but I actually fixed that bug
'''


def add_guild():
    global posts
    guilds = bot.guilds
    dbList = cluster.list_database_names()
    for guild in guilds:
        thisGuild = functions.remove_space(guild.name)
        posts = []
        if thisGuild not in dbList:
            collectionName = f"{thisGuild} Points"
            var = cluster[thisGuild]
            var.create_collection(collectionName)
            this = var[collectionName]
            get_members(guild, this)
        else:
            pass


'''
Whenever a command that uses points is called it has to find the specific user's guild and returns the db and collection
I'm not sure if I need to return the database though.
'''


def find_their_guild(guild_name):
    new_guild_name = functions.remove_space(guild_name)
    if new_guild_name in bot.dbList:
        db = cluster[new_guild_name]
        collection = db[f"{new_guild_name} Points"]
        return db, collection
    else:
        pass


# this just gets a list of all the guilds but actually makes it usable to find it in mongoDB
def list_guilds():
    guilds = bot.guilds
    for guild in guilds:
        guild_name_without_spaces = functions.remove_space(str(guild.name))
        bot.dbList.append(guild_name_without_spaces)
    return bot.dbList


'''
this function is threaded and runs ever 30 minutes, you can change the interval to whatever you want
has to be in seconds though. I haven't fixed it yet to do it for all guids, it currently only does it for one guild
with the given channels. You could copy/paste per channel for each server but that's lame :/
'''


# FIXED (really bro?), now checks through every guild and vc and if someone is in there they get a random int between 90-125 you can change if you want
# TODO: Make this clearer and better
def voice_channel_check():
    voice_channels = []
    for guild in bot.guilds:
        notNeeded, collection = find_their_guild(guild.name)
        for channel in guild.voice_channels:
            voice_channels.append(channel)
        for vc in voice_channels:
            if len(vc.members) > 0:
                for person in vc.members:
                    points = random.randint(90, 125)
                    user_points = functions.show_points(collection.find({"name": person.name})) + points
                    collection.update_one({"name": person.name}, {"$set": {"points": user_points}})
            else:
                pass
        voice_channels = []
    # restarts the function every 30 min
    timer = Timer(1800, voice_channel_check)
    timer.start()


'''
These functions below are used only for refunding,
just takes back the points from the dict and adds them back to DB
and then reset_all_dicts() calls the latter function and clears all dicts afterwards
'''


def reset_all_dicts():
    global_dict.clear()
    refund_dicts()
    believe_pool.clear()
    doubt_pool.clear()


def refund_dicts():
    # refund Believe Pool Points
    for k, v in believe_pool.items():
        user_points = functions.show_points(bot.bet_collection.find({"name": k}))
        bot.bet_collection.update_one({"name": k}, {"$set": {"points": user_points + v}})
    # refund Doubt Pool Points
    for k, v in doubt_pool.items():
        user_points = functions.show_points(bot.bet_collection.find({"name": k}))
        bot.bet_collection.update_one({"name": k}, {"$set": {"points": user_points + v}})


'''
Used for mongoDB which assigns their id name and gives them at least 1000 points, this can be changed
if you want to only assign them their name and increase the amount of points.
'''


def get_members(guild, guildCollection):
    for person in guild.members:
        posts.append({"_id": person.id, "name": person.name, "points": 1000})
    for person in posts:
        guildCollection.insert_one(person)


# basically whenever tries to place a bet it first checks if its past the timer or not, if not then their bets are placed
# TODO: make this return either a bool or a time
def time_check():
    now = datetime.datetime.now()
    if type(bot.end_time) == datetime.datetime and (now < bot.end_time):
        return True
    else:
        return False


'''
After every win it calls the bot collection that was set during $start command and gives the user's percentage of the pool + their own amount that they put in.
Note: I believe that there is some point loss overall since their points are truncated, you don't have to use math.
If you want you can just give them any decimal/leftover points,
but if you want displays to look nice you should format strings involving nums. Do whatever you want with that though I just think its easier this way.
and take into consideration the percentages too if you do.
'''


def give_amount_won(loserPool, winnerPool):
    loserSum = sum(loserPool.values())
    winnerSum = sum(winnerPool.values())
    for k, v in winnerPool.items():
        user_points = functions.show_points(bot.bet_collection.find({"name": k}))
        x = v / winnerSum
        amount = x * loserSum + v
        amount = math.trunc(amount)
        bot.bet_collection.update_one({"name": k}, {"$set": {"points": user_points + amount}})
        payout_pool[k] = amount


class Bot(commands.Bot):
    def __init__(self):
        super(Bot, self).__init__(command_prefix=['$'], intents=intents, case_insensitive=True)
        self.timer, self.end_time, self.start_text = None, None, None
        self.believe_percent, self.doubt_percent, self._last_member = None, None, None
        self.prediction_db, self.bet_collection = None, None
        self.dbList = []
        self.add_cog(Predictions(self))
        self.add_cog(Points(self))

    async def on_ready(self):  # chemotherapy needed here
        print(f'Bot has logged in as {bot.user}')
        add_guild()
        timer = Timer(1800, voice_channel_check)
        timer.start()
        bot.dbList = list_guilds()

    @commands.Cog.listener()
    async def on_guild_join(self):
        add_guild()
        pass


# ALL THE COMMANDS THAT ARE USED FOR PREDICTIONS LIKE STARTING THE BET, BETTING, AND REFUNDING
class Predictions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message = None
        self.start_message = None

    @commands.command(aliases=['set'], description=START_COM_DESCRIPTION)
    async def start(self, ctx, title, t: int, blv, dbt):  # oh god it's metastacized
        bot.prediction_db, bot.bet_collection = find_their_guild(ctx.author.guild.name)
        global_dict['blv'], global_dict['dbt'] = blv, dbt
        global_dict['title'], global_dict['Total'] = title, 0
        bot.timer = t
        bot.end_time = datetime.datetime.now() + datetime.timedelta(seconds=t)
        minutes, secs = divmod(t, 60)
        timer = '{:02d}:{:02d}'.format(minutes, secs)
        text = functions.start_text(title, blv, dbt, timer)
        message = await ctx.send(text)
        while bot.timer >= 0:
            minutes, secs = divmod(bot.timer, 60)
            timer = '{:02d}:{:02d}'.format(minutes, secs)
            time.sleep(1)
            bot.timer -= 1
            await message.edit(content=functions.start_text(title, blv, dbt, timer))
        await ctx.invoke(self.bot.get_command('close_submissions'))

    @start.error
    async def start_error(self, ctx, error):  # just take it out behind the shed
        if isinstance(error, MissingPermissions):
            text = f"Sorry {ctx.message.author.mention}, you do not have permissions to do that!"
            await ctx.send(ctx.message.channel, text)

    # bets on believe
    # another thing to note is that if you bet on dbt, you can't bet blv or if you have no points you aren't allowed to bet
    # it also adds to your previous amount if you have previously bet on this side
    @commands.command(aliases=['believe', 'blv'])
    async def bet_believe(self, ctx, amount: int):  # there's no hope
        user, user_mention, this_time = ctx.message.author.name, ctx.message.author.mention, time_check()
        if this_time:
            user_db = bot.bet_collection.find({"name": user})
            user_points = functions.show_points(user_db)
            user_points -= amount
            if user in doubt_pool:
                text = f"You've chosen your side already {user_mention} <:derp:953081066565038130>"
                await ctx.send(text)
                pass
            elif user_points < 0:
                user_points += amount
                fail_amount_text = f"{user_mention} you don't have that many points... <:sadpepe:942964907463307276> \n" \
                                   f"You have {user_points} points "
                await ctx.send(fail_amount_text)
                pass
            elif user in believe_pool and user_points > 0:
                believe_pool[user] += amount
                global_dict['Total'] += amount
                believe_percent, doubt_percent = functions.percentage(believe_pool, doubt_pool, global_dict)
                text = functions.user_input_points(user_mention, amount, believe_percent, doubt_percent, 'blv', global_dict, believe_pool, doubt_pool)
                bot.bet_collection.update_one({"name": user}, {"$set": {"points": user_points}})
                await ctx.send(text)
                pass
            else:
                global_dict['Total'] += amount
                believe_pool[user] = amount
                believe_percent, doubt_percent = functions.percentage(believe_pool, doubt_pool, global_dict)
                text = functions.user_input_points(user_mention, amount, believe_percent, doubt_percent, 'blv', global_dict, believe_pool, doubt_pool)
                bot.bet_collection.update_one({"name": user}, {"$set": {"points": user_points}})
                await ctx.send(text)
                pass
            pass
        else:
            text = f"{user_mention} Submissions have closed! <:mikesass:907000839246315650>"
            await ctx.send(text)
            pass

    # bets on doubt side
    # another thing to note is that if you bet on blv you can't bet dbt or if you have no points you aren't allowed to bet
    # it also adds to your previous amount if you have previously bet on this side
    @commands.command(aliases=['doubt', 'dbt'])
    async def bet_doubt(self, ctx, amount: int):  # why did I even start?
        user, user_mention, this_time = ctx.message.author.name, ctx.message.author.mention, time_check()
        if this_time:
            user_db = bot.bet_collection.find({"name": user})
            user_points = functions.show_points(user_db)
            user_points -= amount
            if user in believe_pool:
                text = f"You've chosen your side already {user_mention} <:derp:953081066565038130>"
                await ctx.send(text)
                pass
            elif user_points < 0:
                user_points += amount
                fail_amount_text = f"{user_mention} you don't have that many points...<:sadpepe:942964907463307276> \n"\
                                   f"You have {user_points} points "
                await ctx.send(fail_amount_text)
                pass
            elif user in doubt_pool and user_points > 0:
                doubt_pool[user] += amount
                global_dict['Total'] += amount
                believe_percent, doubt_percent = functions.percentage(believe_pool, doubt_pool, global_dict)
                text = functions.user_input_points(user_mention, amount, believe_percent, doubt_percent, 'dbt', global_dict,
                                              believe_pool, doubt_pool)
                bot.bet_collection.update_one({"name": user}, {"$set": {"points": user_points}})
                await ctx.send(text)
                pass
            else:
                global_dict['Total'] += amount
                doubt_pool[user] = amount
                believe_percent, doubt_percent = functions.percentage(believe_pool, doubt_pool, global_dict)
                text = functions.user_input_points(user_mention, amount, believe_percent, doubt_percent, 'dbt', global_dict,
                                              believe_pool, doubt_pool)
                bot.bet_collection.update_one({"name": user}, {"$set": {"points": user_points}})
                await ctx.send(text)
                pass
            pass
        else:
            text = f"{user_mention} Submissions have closed! <:mikesass:907000839246315650>"
            await ctx.send(text)
            pass

    # set winner command
    @commands.command(name='won', description=WON_COM_DESCRIPTION)
    async def winner(self, ctx, side: str):
        pool, title, blv, dbt, believe_sum, doubt_sum = functions.return_values(believe_pool, doubt_pool, global_dict)
        believe_percent, doubt_percent = functions.percentage(believe_pool, doubt_pool, global_dict)
        # TODO: Big DRY
        if side == "believe" or side == "blv":
            give_amount_won(doubt_pool, believe_pool)
            winner_text = functions.return_win_text(title, blv, believe_percent, doubt_percent, 'blv', believe_pool, doubt_pool, payout_pool)
            bot.believe_percent, bot.doubt_percent = None, None
            functions.reset_after_win(global_dict, believe_pool, doubt_pool, payout_pool)
            await ctx.send(winner_text)
            pass
        elif side == "doubt" or side == "dbt":
            give_amount_won(believe_pool, doubt_pool)
            winner_text = functions.return_win_text(title, dbt, believe_percent, doubt_percent, 'dbt', believe_pool, doubt_pool, payout_pool)
            bot.believe_percent, bot.doubt_percent = None, None
            functions.reset_after_win(global_dict, believe_pool, doubt_pool, payout_pool)
            await ctx.send(winner_text)
            pass

    @winner.error
    async def winner_error(self, ctx, error):
        if isinstance(error, MissingPermissions):
            text = f"Sorry {ctx.message.author.mention}, you do not have permissions to do that!"
            await ctx.send(text)
            pass

    @commands.command(aliases=['reset'], description=REFUND_COM_DESCRIPTION)
    async def refund(self, ctx):
        reset_all_dicts()
        bot.believe_percent, bot.doubt_percent = None, None
        refund_text = "The prediction has ended early, refunding your chichens <:sadpepe:942964907463307276>"
        await ctx.send(refund_text)

    @refund.error
    async def refund_error(self, ctx, error):
        if isinstance(error, MissingPermissions):
            text = f"Sorry {ctx.message.author.mention}, you do not have permissions to do that!"
            await ctx.send(ctx.message.channel, text)

    @commands.command(aliases=['close', 'stop'])
    async def close_submissions(self, ctx):
        end_text = functions.end_text(believe_pool, doubt_pool, global_dict)
        if bot.timer == 0:
            await ctx.send(end_text)
        else:
            bot.end_time = bot.end_time - datetime.timedelta(seconds=bot.timer)
            bot.timer = 0
            await ctx.send(end_text)
        bot.end_time, bot.timer = None, None

    @close_submissions.error
    async def close_error(self, ctx, error):
        if isinstance(error, MissingPermissions):
            text = f"Sorry {ctx.message.author.mention}, you do not have permissions to do that!"
            await ctx.send(ctx.message.channel, text)


# this cog basically displays points, takes and gives
class Points(commands.Cog):
    def __init__(self, bot):
        self.message = None
        self.bot = bot
        self.user_collection = None
        self.user_db = None

    @commands.command(name='give', description=GIVE_COM_DESCRIPTION)
    async def give_points(self, ctx, give_Member: str, amount: int):
        bot.user_db, bot.user_collection = find_their_guild(ctx.author.guild.name)
        thisMember = bot.user_collection.find({"name": give_Member})
        user_points = functions.show_points(thisMember) + amount
        bot.user_collection.update_one({"name": give_Member}, {"$set": {"points": user_points}})
        text = f"{give_Member} you have {user_points} chichens <:fire_chichen:941754253729497188> <:fire_chichen:941754253729497188> <:fire_chichen:941754253729497188> <:fire_chichen:941754253729497188>"
        await ctx.send(text)

    @give_points.error
    async def give_error(self, ctx, error):
        if isinstance(error, MissingPermissions):
            text = f"Sorry {ctx.message.author.mention}, you do not have permissions to do that!"
            await ctx.send(text)
            pass

    # I haven't actually considered if they take more than what they have so be aware of that not that important to me at the moment
    @commands.command(name='take', description="Takes points from specific member, you have to type their discord NAME (Only admins can use).")
    @has_permissions(manage_roles=True, ban_members=True)
    async def take_points(self, ctx, take_Member: str, amount: int):
        bot.user_db, bot.user_collection = find_their_guild(ctx.author.guild.name)
        thisMember = bot.user_collection.find({"name": take_Member})
        user_points = functions.show_points(thisMember) - amount
        bot.user_collection.update_one({"name": take_Member}, {"$set": {"points": user_points}})
        text = f"{take_Member} you have {user_points} chichens <:fire_chichen:941754253729497188> <:sadpepe:942964907463307276>"
        await ctx.send(text)

    @take_points.error
    async def give_error(self, ctx, error):
        if isinstance(error, MissingPermissions):
            text = f"Sorry {ctx.message.author.mention}, you do not have permissions to do that!"
            await ctx.send(text)
            pass

    @commands.command(aliases=['chichens','points', 'pts', 'chichen'], description="Shows your chichens")
    async def ask_chicken(self, ctx):
        user, user_mention = ctx.message.author.name, ctx.message.author.mention
        bot.user_db, bot.user_collection = find_their_guild(ctx.author.guild.name)
        thisMember = bot.user_collection.find({"name": user})
        user_points = functions.show_points(thisMember)
        text = f"{user_mention} you have {user_points} chichens <:fire_chichen:941754253729497188>"
        await ctx.send(text)

keep_alive()
bot = Bot()
bot.run(TOKEN)

#############################
# UNUSED functions/COMMANDS #
#############################

""" @commands.Cog.listener()
    @commands.has_any_role(['Lettuce', 'Top Dogs'])
    @commands.cooldown(1, 120, commands.BucketType.user)
    async def on_message(self, message):
        user = message.author.name
        if user in memberDict.keys():
            memberDict[user] += random.randint(25, 50)
        print(memberDict)
"""

