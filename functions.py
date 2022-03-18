import math


# whenever a user bets it sends this text I just added the semantics part just in case someone already had bet
def user_input_points(user, amount, believe_percent, doubt_percent, side, global_dict, believe_pool, doubt_pool):
    text = f"{user} has added to the pool with **{amount} points! on \"{global_dict[side]}\"** <:vhard:613718800298147890> \n" \
           f"```autohotkey\n" \
           f"Total Pool: {global_dict['Total']} points\n" \
           f"Blv Percent/People/Amount: {believe_percent}%, {len(believe_pool)}, {sum(believe_pool.values())}\n" \
           f"Dbt Percent/People/Amount: {doubt_percent}%, {len(doubt_pool)}, {sum(doubt_pool.values())} ```"
    return text


# for $start command text
def start_text(title, blv, dbt, timer):
    text = f"> Prediction Started: **{title}?** Time Left: **{timer}**\n" \
           f"```bash\n" \
           f"Type $believe (amount) to bet on \"{blv}\"\n" \
           f"Type $doubt (amount) to bet on \"{dbt}\"\n" \
           f"Type $points to check how many points you have```"
    return text


# there are a lot of values to be summoned for the win command so I decided to make a function for a one liner
# makes it simpler
def return_values(believe_pool, doubt_pool, global_dict):
    pool, title = global_dict['Total'], global_dict['title']
    blv, dbt = global_dict['blv'], global_dict['dbt']
    believe_sum, doubt_sum = sum(believe_pool.values()), sum(doubt_pool.values())
    return pool, title, blv, dbt, believe_sum, doubt_sum


# i just want to say this looks so nice it looks like a block
# gets the percentages of the pool and returns their values
def percentage(believe_pool, doubt_pool, global_dict):
    blv = sum(believe_pool.values())
    dbt = sum(doubt_pool.values())
    poolSize = global_dict['Total']
    blv = (blv / poolSize) * 100
    dbt = (dbt / poolSize) * 100
    doubt_percent = math.trunc(dbt)
    believe_percent = math.trunc(blv)
    return believe_percent, doubt_percent


# different from refund as it doesn't give back points from dict to DB it transfers to winner users
def reset_after_win(global_dict, believe_pool, doubt_pool, payout_pool):
    global_dict.clear()
    believe_pool.clear()
    doubt_pool.clear()
    payout_pool.clear()


# shows title result percentages, biggest payout
def return_win_text(title, result, believe_percent, doubt_percent, side, believe_pool, doubt_pool, payout_pool):
    global winner
    maxVal = max(payout_pool.values())
    biggestWinner = max(payout_pool, key=payout_pool.get)
    if side == 'blv':
        winner = "Believers"
    elif side == 'dbt':
        winner = "Doubters"
    winnerText = f"```autohotkey\n" \
                 f"Prediction results: {winner} Won!\n" \
                 f"Title: \"{title}?\"\n" \
                 f"result: \"{result}\"\n" \
                 f"Biggest Pay out: {biggestWinner} with +{maxVal} points\n" \
                 f"Blv Percent/People/Amount: {believe_percent}%, {len(believe_pool)}, {sum(believe_pool.values())} points\n" \
                 f"Dbt Percent/People/Amount: {doubt_percent}%, {len(doubt_pool)}, {sum(doubt_pool.values())} points ```"
    return winnerText


# I want to use this command whenever the timer has ended
def end_text(believe_pool, doubt_pool, global_dict):
    believe_percent, doubt_percent = percentage(believe_pool, doubt_pool, global_dict)
    text = f"> Submissions Closed!: **{global_dict['title']}?**\n" \
           f"```autohotkey\n" \
           f"Total Pool: {global_dict['Total']} points\n" \
           f"Blv Percent/People/Amount: {believe_percent}%, {len(believe_pool)}, {sum(believe_pool.values())}\n" \
           f"Dbt Percent/People/Amount: {doubt_percent}%, {len(doubt_pool)}, {sum(doubt_pool.values())} ```"
    return text


# finds the post attribute and just returns the value
def show_points(post):
    for i in post:
        return i["points"]


# used to find the database for guild since some guilds might have spaces in them
def remove_space(string):
    newString = string.replace(" ", "")
    return newString

