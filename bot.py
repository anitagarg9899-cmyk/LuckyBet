import discord
from discord.ext import commands
import random
import json
import os
from datetime import datetime

# Debug/version stamp for redeploy detection
VERSION = "v1.1-redeploy-2026-06-09T11:15:00Z"

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='.', intents=intents)

# Database file for user balances
DB_FILE = 'user_data.json'

# Currency conversion rates (Points to USD)
CURRENCY_RATES = {
    1: 0.0037,
    100: 0.37,
    1000: 3.70,
    10000: 37.00,
    100000: 370.00,
    1000000: 3700.00
}

def load_data():
    """Load user data from JSON file"""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_data(data):
    """Save user data to JSON file"""
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_user_balance(user_id):
    """Get user's current balance"""
    data = load_data()
    return data.get(str(user_id), {}).get('balance', 1000)

def set_user_balance(user_id, amount):
    """Set user's balance"""
    data = load_data()
    user_id_str = str(user_id)
    if user_id_str not in data:
        data[user_id_str] = {'balance': 1000, 'stats': {'wins': 0, 'losses': 0, 'total_wagered': 0}}
    data[user_id_str]['balance'] = amount
    save_data(data)

def add_to_stats(user_id, result, wager):
    """Update user statistics"""
    data = load_data()
    user_id_str = str(user_id)
    if user_id_str not in data:
        data[user_id_str] = {'balance': 1000, 'stats': {'wins': 0, 'losses': 0, 'total_wagered': 0}}
    
    data[user_id_str]['stats']['total_wagered'] += wager
    if result:
        data[user_id_str]['stats']['wins'] += 1
    else:
        data[user_id_str]['stats']['losses'] += 1
    save_data(data)

def convert_points_to_usd(points):
    """Convert points to USD based on conversion rates"""
    # Find the best matching rate
    sorted_rates = sorted(CURRENCY_RATES.keys())
    
    if points < sorted_rates[0]:
        # Less than 1 point
        rate = CURRENCY_RATES[sorted_rates[0]] / sorted_rates[0]
        return points * rate
    
    for i, key in enumerate(sorted_rates):
        if points == key:
            return CURRENCY_RATES[key]
        elif i < len(sorted_rates) - 1 and sorted_rates[i] < points < sorted_rates[i + 1]:
            # Interpolate between rates
            rate = CURRENCY_RATES[key] / key
            return points * rate
    
    # Greater than largest amount - use the last rate
    rate = CURRENCY_RATES[sorted_rates[-1]] / sorted_rates[-1]
    return points * rate

@bot.event
async def on_ready():
    # Print a visible version stamp so we can confirm which commit is running
    print(f'{bot.user} has connected to Discord! -- {VERSION}')
    print('------')

@bot.command(name='balance', help='Check your current balance')
async def balance(ctx):
    """Display user's balance"""
    user_balance = get_user_balance(ctx.author.id)
    embed = discord.Embed(
        title="💰 Your Balance",
        description=f"**{ctx.author.name}**, you have **${user_balance}** LuckyBucks!",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)

@bot.command(name='price', help='Convert LuckyBucks to USD! Usage: .price <amount>')
async def price(ctx, amount: int = None):
    """Convert points to USD"""
    if amount is None:
        # Show price table
        embed = discord.Embed(
            title="💵 LuckyBet Price Table",
            description="Conversion rates from LuckyBucks to USD",
            color=discord.Color.blue()
        )
        
        price_text = "```
Points                  R$         USD
"
        price_text += "--------------------------------------
"
        
        for points, usd in CURRENCY_RATES.items():
            real_value = f"R${points:,}"
            price_text += f"{points:<20} {real_value:<13} ${usd:.2f}\n"
        
        price_text += "```"
        
        embed.description = price_text
        await ctx.send(embed=embed)
        return
    
    if amount <= 0:
        await ctx.send("❌ Amount must be positive!")
        return
    
    # Convert specific amount
    usd_value = convert_points_to_usd(amount)
    real_value = amount  # If you have a different exchange rate, update this
    
    embed = discord.Embed(
        title="💱 Price Conversion",
        color=discord.Color.gold()
    )
    embed.add_field(name="LuckyBucks", value=f"**{amount:,}** points", inline=True)
    embed.add_field(name="Brazilian Real", value=f"**R${amount:,.2f}**", inline=True)
    embed.add_field(name="USD", value=f"**${usd_value:.2f}**", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='coinflip', help='Flip a coin! Usage: .coinflip <amount> <heads/tails>')
async def coinflip(ctx, amount: int, choice: str):
    """Coin flip game"""
    user_balance = get_user_balance(ctx.author.id)
    choice = choice.lower()
    
    if choice not in ['heads', 'tails', 'h', 't']:
        await ctx.send("❌ Please choose **heads** or **tails** (or h/t)")
        return
    
    if amount <= 0:
        await ctx.send("❌ Bet amount must be positive!")
        return
    
    if amount > user_balance:
        await ctx.send(f"❌ You don't have enough LuckyBucks! Your balance: ${user_balance}")
        return
    
    choice = 'heads' if choice == 'h' else ('tails' if choice == 't' else choice)
    result = random.choice(['heads', 'tails'])
    won = choice == result
    
    if won:
        new_balance = user_balance + amount
        add_to_stats(ctx.author.id, True, amount)
        embed = discord.Embed(
            title="🎉 Coin Flip - YOU WON!",
            description=f"You chose **{choice}** and got **{result}**!",
            color=discord.Color.green()
        )
        embed.add_field(name="Winnings", value=f"+${amount}", inline=False)
        embed.add_field(name="New Balance", value=f"${new_balance}", inline=False)
    else:
        new_balance = user_balance - amount
        add_to_stats(ctx.author.id, False, amount)
        embed = discord.Embed(
            title="😢 Coin Flip - YOU LOST!",
            description=f"You chose **{choice}** but got **{result}**!",
            color=discord.Color.red()
        )
        embed.add_field(name="Lost", value=f"-${amount}", inline=False)
        embed.add_field(name="New Balance", value=f"${new_balance}", inline=False)
    
    set_user_balance(ctx.author.id, new_balance)
    await ctx.send(embed=embed)

@bot.command(name='dice', help='Roll dice! Usage: .dice <amount> <1-6>')
async def dice(ctx, amount: int, guess: int):
    """Dice roll game"""
    user_balance = get_user_balance(ctx.author.id)
    
    if guess < 1 or guess > 6:
        await ctx.send("❌ Please guess a number between 1 and 6!")
        return
    
    if amount <= 0:
        await ctx.send("❌ Bet amount must be positive!")
        return
    
    if amount > user_balance:
        await ctx.send(f"❌ You don't have enough LuckyBucks! Your balance: ${user_balance}")
        return
    
    roll = random.randint(1, 6)
    won = guess == roll
    
    if won:
        winnings = amount * 5
        new_balance = user_balance + winnings
        add_to_stats(ctx.author.id, True, amount)
        embed = discord.Embed(
            title="🎉 Dice Roll - YOU WON!",
            description=f"You guessed **{guess}** and rolled **{roll}**!",
            color=discord.Color.green()
        )
        embed.add_field(name="Winnings", value=f"+${winnings}", inline=False)
        embed.add_field(name="New Balance", value=f"${new_balance}", inline=False)
    else:
        new_balance = user_balance - amount
        add_to_stats(ctx.author.id, False, amount)
        embed = discord.Embed(
            title="😢 Dice Roll - YOU LOST!",
            description=f"You guessed **{guess}** but rolled **{roll}**!",
            color=discord.Color.red()
        )
        embed.add_field(name="Lost", value=f"-${amount}", inline=False)
        embed.add_field(name="New Balance", value=f"${new_balance}", inline=False)
    
    set_user_balance(ctx.author.id, new_balance)
    await ctx.send(embed=embed)

@bot.command(name='slots', help='Play slot machine! Usage: .slots <amount>')
async def slots(ctx, amount: int):
    """Slot machine game"""
    user_balance = get_user_balance(ctx.author.id)
    
    if amount <= 0:
        await ctx.send("❌ Bet amount must be positive!")
        return
    
    if amount > user_balance:
        await ctx.send(f"❌ You don't have enough LuckyBucks! Your balance: ${user_balance}")
        return
    
    symbols = ['🍎', '🍊', '🍋', '🍌', '⭐', '💎']
    result = [random.choice(symbols) for _ in range(3)]
    
    # Calculate winnings
    if result[0] == result[1] == result[2]:
        if result[0] == '💎':
            winnings = amount * 100
        else:
            winnings = amount * 10
        won = True
    elif result[0] == result[1] or result[1] == result[2]:
        winnings = amount * 2
        won = True
    else:
        winnings = 0
        won = False
    
    if won:
        new_balance = user_balance + winnings
        add_to_stats(ctx.author.id, True, amount)
        embed = discord.Embed(
            title="🎉 Slot Machine - YOU WON!",
            description=f"{result[0]} {result[1]} {result[2]}",
            color=discord.Color.green()
        )
        embed.add_field(name="Winnings", value=f"+${winnings}", inline=False)
        embed.add_field(name="New Balance", value=f"${new_balance}", inline=False)
    else:
        new_balance = user_balance - amount
        add_to_stats(ctx.author.id, False, amount)
        embed = discord.Embed(
            title="😢 Slot Machine - YOU LOST!",
            description=f"{result[0]} {result[1]} {result[2]}",
            color=discord.Color.red()
        )
        embed.add_field(name="Lost", value=f"-${amount}", inline=False)
        embed.add_field(name="New Balance", value=f"${new_balance}", inline=False)
    
    set_user_balance(ctx.author.id, new_balance)
    await ctx.send(embed=embed)

@bot.command(name='roulette', help='Play roulette! Usage: .roulette <amount> <red/black/even/odd>')
async def roulette(ctx, amount: int, choice: str):
    """Roulette game"""
    user_balance = get_user_balance(ctx.author.id)
    choice = choice.lower()
    
    valid_choices = ['red', 'black', 'even', 'odd']
    if choice not in valid_choices:
        await ctx.send(f"❌ Please choose: {', '.join(valid_choices)}")
        return
    
    if amount <= 0:
        await ctx.send("❌ Bet amount must be positive!")
        return
    
    if amount > user_balance:
        await ctx.send(f"❌ You don't have enough LuckyBucks! Your balance: ${user_balance}")
        return
    
    # Spin the wheel (1-36, 0 is green)
    spin = random.randint(0, 36)
    
    # Determine result
    if spin == 0:
        result = "green"
        won = False
    else:
        result = "red" if spin % 2 == 1 else "black"
        parity = "even" if spin % 2 == 0 else "odd"
        won = (choice == result) or (choice == parity)
    
    if won:
        winnings = amount * 2
        new_balance = user_balance + winnings
        add_to_stats(ctx.author.id, True, amount)
        embed = discord.Embed(
            title="🎉 Roulette - YOU WON!",
            description=f"The wheel landed on **{spin}** ({result})!",
            color=discord.Color.green()
        )
        embed.add_field(name="Winnings", value=f"+${winnings}", inline=False)
        embed.add_field(name="New Balance", value=f"${new_balance}", inline=False)
    else:
        new_balance = user_balance - amount
        add_to_stats(ctx.author.id, False, amount)
        result_str = "green" if spin == 0 else f"{spin} ({result})"
        embed = discord.Embed(
            title="😢 Roulette - YOU LOST!",
            description=f"The wheel landed on **{result_str}**!",
            color=discord.Color.red()
        )
        embed.add_field(name="Lost", value=f"-${amount}", inline=False)
        embed.add_field(name="New Balance", value=f"${new_balance}", inline=False)
    
    set_user_balance(ctx.author.id, new_balance)
    await ctx.send(embed=embed)

@bot.command(name='blackjack', help='Play blackjack! Usage: .blackjack <amount>')
async def blackjack(ctx, amount: int):
    """Blackjack game"""
    user_balance = get_user_balance(ctx.author.id)
    
    if amount <= 0:
        await ctx.send("❌ Bet amount must be positive!")
        return
    
    if amount > user_balance:
        await ctx.send(f"❌ You don't have enough LuckyBucks! Your balance: ${user_balance}")
        return
    
    deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
    random.shuffle(deck)
    
    def card_value(cards):
        total = sum(cards)
        aces = cards.count(11)
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total
    
    player_cards = [deck.pop(), deck.pop()]
    dealer_cards = [deck.pop(), deck.pop()]
    
    player_value = card_value(player_cards)
    
    # Check for blackjack
    if player_value == 21:
        winnings = amount * 2
        new_balance = user_balance + winnings
        add_to_stats(ctx.author.id, True, amount)
        embed = discord.Embed(
            title="🎉 Blackjack - YOU WIN!",
            description="You got **Blackjack**!",
            color=discord.Color.green()
        )
        embed.add_field(name="Your Cards", value=f"{player_cards}", inline=False)
        embed.add_field(name="Winnings", value=f"+${winnings}", inline=False)
        embed.add_field(name="New Balance", value=f"${new_balance}", inline=False)
        set_user_balance(ctx.author.id, new_balance)
        await ctx.send(embed=embed)
        return
    
    # Dealer plays
    while card_value(dealer_cards) < 17:
        dealer_cards.append(deck.pop())
    
    dealer_value = card_value(dealer_cards)
    
    # Determine winner
    if player_value > 21:
        won = False
        result = "You busted!"
    elif dealer_value > 21:
        won = True
        result = "Dealer busted!"
    elif player_value > dealer_value:
        won = True
        result = "You have a higher hand!"
    elif player_value < dealer_value:
        won = False
        result = "Dealer has a higher hand!"
    else:
        won = False
        result = "It's a tie!"
    
    if won:
        winnings = amount * 2
        new_balance = user_balance + winnings
        add_to_stats(ctx.author.id, True, amount)
        embed = discord.Embed(
            title="🎉 Blackjack - YOU WIN!",
            description=result,
            color=discord.Color.green()
        )
        embed.add_field(name="Your Cards", value=f"{player_cards} (**{player_value}**)", inline=False)
        embed.add_field(name="Dealer Cards", value=f"{dealer_cards} (**{dealer_value}**)", inline=False)
        embed.add_field(name="Winnings", value=f"+${winnings}", inline=False)
        embed.add_field(name="New Balance", value=f"${new_balance}", inline=False)
    else:
        new_balance = user_balance - amount
        add_to_stats(ctx.author.id, False, amount)
        embed = discord.Embed(
            title="😢 Blackjack - YOU LOST!",
            description=result,
            color=discord.Color.red()
        )
        embed.add_field(name="Your Cards", value=f"{player_cards} (**{player_value}**)", inline=False)
        embed.add_field(name="Dealer Cards", value=f"{dealer_cards} (**{dealer_value}**)", inline=False)
        embed.add_field(name="Lost", value=f"-${amount}", inline=False)
        embed.add_field(name="New Balance", value=f"${new_balance}", inline=False)
    
    set_user_balance(ctx.author.id, new_balance)
    await ctx.send(embed=embed)

@bot.command(name='leaderboard', help='View top 10 players')
async def leaderboard(ctx):
    """Display leaderboard"""
    data = load_data()
    
    if not data:
        await ctx.send("❌ No players yet!")
        return
    
    # Sort by balance
    sorted_players = sorted(data.items(), key=lambda x: x[1]['balance'], reverse=True)[:10]
    
    leaderboard_text = ""
    for idx, (user_id, user_data) in enumerate(sorted_players, 1):
        try:
            user = await bot.fetch_user(int(user_id))
            leaderboard_text += f"**{idx}.** {user.name} - ${user_data['balance']}\n"
        except:
            leaderboard_text += f"**{idx}.** Unknown User - ${user_data['balance']}\n"
    
    embed = discord.Embed(
        title="🏆 LuckyBet Leaderboard",
        description=leaderboard_text,
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)

@bot.command(name='stats', help='View your statistics')
async def stats(ctx):
    """Display user statistics"""
    data = load_data()
    user_id_str = str(ctx.author.id)
    
    if user_id_str not in data:
        await ctx.send("❌ You haven't played any games yet!")
        return
    
    user_data = data[user_id_str]
    stats_data = user_data['stats']
    
    total_games = stats_data['wins'] + stats_data['losses']
    win_rate = (stats_data['wins'] / total_games * 100) if total_games > 0 else 0
    
    embed = discord.Embed(
        title="📊 Your Statistics",
        color=discord.Color.blue()
    )
    embed.add_field(name="Balance", value=f"${user_data['balance']}", inline=True)
    embed.add_field(name="Total Games", value=total_games, inline=True)
    embed.add_field(name="Wins", value=stats_data['wins'], inline=True)
    embed.add_field(name="Losses", value=stats_data['losses'], inline=True)
    embed.add_field(name="Win Rate", value=f"{win_rate:.1f}%", inline=True)
    embed.add_field(name="Total Wagered", value=f"${stats_data['total_wagered']}", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='help', help='Show all commands')
async def help_command(ctx):
    """Display help message"""
    embed = discord.Embed(
        title="🎰 LuckyBet Bot - Commands",
        color=discord.Color.purple()
    )
    embed.add_field(name=".balance", value="Check your current balance", inline=False)
    embed.add_field(name=".price", value="View price table", inline=False)
    embed.add_field(name=".price <amount>", value="Convert LuckyBucks to USD", inline=False)
    embed.add_field(name=".coinflip <amount> <heads/tails>", value="Flip a coin (1:1 odds)", inline=False)
    embed.add_field(name=".dice <amount> <1-6>", value="Roll a dice (5:1 payout)", inline=False)
    embed.add_field(name=".slots <amount>", value="Play slot machine", inline=False)
    embed.add_field(name=".roulette <amount> <red/black/even/odd>", value="Play roulette (2:1 payout)", inline=False)
    embed.add_field(name=".blackjack <amount>", value="Play blackjack (2:1 payout)", inline=False)
    embed.add_field(name=".leaderboard", value="View top 10 players", inline=False)
    embed.add_field(name=".stats", value="View your personal statistics", inline=False)
    embed.add_field(name="Starting Balance", value="Everyone starts with $1000", inline=False)
    
    await ctx.send(embed=embed)

# Run the bot
if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if not TOKEN:
        print("❌ Please set the DISCORD_BOT_TOKEN environment variable!")
    else:
        bot.run(TOKEN)
