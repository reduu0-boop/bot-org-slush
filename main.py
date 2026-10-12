import discord
from discord.ext import commands
import os
import asyncio

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

CANAL_SUPORTE = "suporte"
VALORES = [0.20, 0.40, 0.70, 1.00, 2.00, 3.00, 4.00, 5.00, 7.00, 10.00, 14.00, 19.00, 30.00, 50.00, 70.00, 100.00, 150.00, 200.00]
filas = {}

def formatar(v): return f"R$ {v:.2f}".replace('.', ',')
def get_qtd(nome):
    n = nome.lower()
    if "1x1" in n: return 2
    if "2x2" in n: return 4
    if "3x3" in n: return 6
    if "4x4" in n: return 8
    return 2
def get_canais_fila(guild):
    return [c for c in guild.text_channels if "x" in c.name.lower() and ("mobile" in c.name.lower() or "misto" in c.name.lower() or "emulador" in c.name.lower())]
def get_fila(canal_id, valor):
    if canal_id not in filas: filas[canal_id] = {}
    if valor not in filas[canal_id]: filas[canal_id][valor] = {"Gelo Infinito": [], "Gelo Normal": []}
    return filas[canal_id][valor]

class FilaView(discord.ui.View):
    def __init__(self, canal_id, valor):
        super().__init__(timeout=None)
        self.canal_id = canal_id
        self.valor = valor
    @discord.ui.button(label="Gelo Infinito", style=discord.ButtonStyle.secondary, emoji="🧊")
    async def infinito(self, i, b): await self.entrar(i, "Gelo Infinito")
    @discord.ui.button(label="Gelo Normal", style=discord.ButtonStyle.secondary, emoji="🧊")
    async def normal(self, i, b): await self.entrar(i, "Gelo Normal")
    @discord.ui.button(label="Sair", style=discord.ButtonStyle.red, emoji="🚪")
    async def sair(self, i, b):
        f = get_fila(self.canal_id, self.valor)
        u = i.user
        saiu=False
        for t in f:
            if u in f[t]: f[t].remove(u); saiu=True
        if saiu:
            await i.response.send_message(f"Saiu da fila {formatar(self.valor)}", ephemeral=True)
            await atualizar_canal(i.guild.get_channel(self.canal_id))
        else:
            await i.response.send_message("Você não está na fila!", ephemeral=True)
    async def entrar(self, interaction, tipo):
        f = get_fila(self.canal_id, self.valor)
        u = interaction.user
        for t in f:
            if u in f[t]: f[t].remove(u)
        f[tipo].append(u)
        await interaction.response.send_message(f"Entrou: {formatar(self.valor)} - {tipo}", ephemeral=True)
        canal = interaction.guild.get_channel(self.canal_id)
        qtd_needed = get_qtd(canal.name)
        if len(f[tipo]) >= qtd_needed:
            jogadores = f[tipo][:qtd_needed]
            f[tipo] = f[tipo][qtd_needed:]
            mencoes = " ".join([j.mention for j in jogadores])
            embed = discord.Embed(title="🔔 PARTIDA ENCONTRADA!", description=f"**Canal:** {canal.mention}\n**Valor:** {formatar(self.valor)}\n**Modo:** {tipo}\n**Jogadores:** {mencoes}\n\nStaff digite `!sala ID SENHA`", color=0x00FF00)
            await canal.send(content=mencoes, embed=embed)
        await atualizar_canal(canal)

async def atualizar_canal(channel):
    if not channel: return
    cid = channel.id
    async for msg in channel.history(limit=50):
        if msg.author == bot.user and msg.embeds and "• R$" in msg.embeds[0].title:
            try: await msg.delete()
            except: pass
    for valor in VALORES:
        f = get_fila(cid, valor)
        embed = discord.Embed(title=f"{channel.name.upper()} • {formatar(valor)}", color=0x2F3136)
        texto=""; tem=False
        for tipo in ["Gelo Infinito", "Gelo Normal"]:
            if f[tipo]:
                tem=True
                lista="\n".join([f"{j.mention}" for j in f[tipo]])
                texto+=f"**{tipo} ({len(f[tipo])}/{get_qtd(channel.name)}):**\n{lista}\n\n"
        if not tem: embed.add_field(name="Jogadores", value="Nenhum jogador na fila.", inline=False)
        else: embed.add_field(name="Jogadores", value=texto, inline=False)
        await channel.send(embed=embed, view=FilaView(cid, valor))

class TicketView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.blurple, emoji="🎫", custom_id="ticket_abrir")
    async def abrir(self, i, b):
        guild=i.guild
        overwrites={guild.default_role: discord.PermissionOverwrite(view_channel=False), i.user: discord.PermissionOverwrite(view_channel=True, send_messages=True), guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)}
        cat = discord.utils.get(guild.categories, name="Tickets")
        canal = await guild.create_text_channel(f"ticket-{i.user.name}", overwrites=overwrites, category=cat)
        await canal.send(embed=discord.Embed(title="Suporte ORG SLUSH", description=f"{i.user.mention} Explique seu problema!\n`!fechar` pra fechar.", color=0x00FF00))
        await i.response.send_message(f"Ticket criado: {canal.mention}", ephemeral=True)

async def setup_suporte_func(guild):
    canal_sup = discord.utils.find(lambda c: CANAL_SUPORTE in c.name.lower(), guild.text_channels)
    if not canal_sup: return
    async for m in canal_sup.history(limit=20):
        try: await m.delete()
        except: pass
    embed = discord.Embed(title="📢 SUPORTE ORG SLUSH", description="Precisa de ajuda?\nClique abaixo para abrir um ticket privado.\n\n**Não mande mensagem aqui, use o botão!**", color=0x2B88D8)
    await canal_sup.send(embed=embed, view=TicketView())

@bot.event
async def on_ready():
    print(f"Bot ON: {bot.user}")
    bot.add_view(TicketView())

@bot.event
async def on_message(message):
    if message.author.bot:
        await bot.process_commands(message)
        return
    if CANAL_SUPORTE in message.channel.name.lower():
        if not message.author.guild_permissions.manage_messages:
            try:
                await message.delete()
            except: pass
            return
    await bot.process_commands(message)

@bot.command()
async def fechar(ctx):
    if "ticket-" in ctx.channel.name:
        await ctx.send("Fechando em 3s...")
        await asyncio.sleep(3)
        await ctx.channel.delete()

@bot.command()
async def sala(ctx, id_sala: str, senha: str):
    if not ctx.author.guild_permissions.manage_messages: return
    embed = discord.Embed(title="🎮 SALA CRIADA!", description=f"**ID:** `{id_sala}`\n**Senha:** `{senha}`", color=0xFF0000)
    await ctx.send(content="@here", embed=embed)

@bot.command()
async def setup_tudo(ctx):
    if not ctx.author.guild_permissions.administrator: return
    await ctx.send("Configurando...")
    await setup_suporte_func(ctx.guild)
    for ch in get_canais_fila(ctx.guild):
        await atualizar_canal(ch)
    await ctx.send("✅ ORG SLUSH 100% configurada!")

bot.run(os.getenv("DISCORD_TOKEN"))
