import discord
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"org slush online como {bot.user}")
    await bot.change_presence(activity=discord.Game(name="suporte ORG SLUSH"))
    try:
        await bot.tree.sync()
        print("Comandos sincronizados!")
    except Exception as e:
        print(e)

@bot.tree.command(name="ticket", description="Abrir um ticket de suporte")
async def ticket(interaction: discord.Interaction):
    guild = interaction.guild
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
    }
    # Libera pra cargos de staff/suporte/adm se existir
    for role in guild.roles:
        nome = role.name.lower()
        if "staff" in nome or "suporte" in nome or "adm" in nome or "mod" in nome:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    channel = await guild.create_text_channel(f"ticket-{interaction.user.name}", overwrites=overwrites, reason=f"Ticket de {interaction.user}")
    await interaction.response.send_message(f"Seu ticket foi criado: {channel.mention}", ephemeral=True)
    await channel.send(f"{interaction.user.mention} Bem-vindo ao suporte ORG SLUSH! Explique seu problema aqui. Digite `!fechar` para fechar.")

@bot.command()
async def fechar(ctx):
    if "ticket-" in ctx.channel.name.lower():
        await ctx.send("Fechando ticket em 3 segundos...")
        import asyncio
        await asyncio.sleep(3)
        await ctx.channel.delete(reason="Ticket fechado")
    else:
        await ctx.send("Isso só pode ser usado em canal de ticket.")

bot.run(os.getenv("TOKEN"))
