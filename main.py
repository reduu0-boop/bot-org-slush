import discord
from discord.ext import commands
import os
import asyncio

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

CANAL_SUPORTE = "suporte"
VALORES = [0.20, 0.40, 0.70, 1.00, 2.00, 3.00, 4.00, 5.00, 7.00, 10.00, 14.00, 19.00, 30.00, 50.00, 70.00, 100.00, 150.00, 200.00]
filas = {}

def formatar(v): return f"R$ {v:.2f}".replace('.', ',')
def get_qtd(nome):
    n=nome.lower()
    if "1x1" in n: return 2
    if "2x2" in n: return 4
    if "3x3" in n: return 6
    if "4x4" in n: return 8
    return 2
def get_canais_fila(guild):
    return [c for c in guild.text_channels if "x" in c.name.lower() and ("mobile" in c.name.lower() or "misto" in c.name.lower() or "emulador" in c.name.lower())]
def get_fila(cid, valor):
    if cid not in filas: filas[cid] = {}
    if valor not in filas[cid]: filas[cid][valor] = {"Gelo Infinito": [], "Gelo Normal": []}
    return filas[cid][valor]

def build_embed(channel, valor):
    f = get_fila(channel.id, valor)
    emb = discord.Embed(title=f"{channel.name.upper()} • {formatar(valor)}", color=0x2F3136)
    txt = ""
    for tipo in ["Gelo Infinito", "Gelo Normal"]:
        if f[tipo]:
            txt += f"**{tipo} ({len(f[tipo])}/{get_qtd(channel.name)}):**\n"
            for u in f[tipo]:
                txt += f"{u.mention}\n"
            txt += "\n"
    if not txt: txt = "Nenhum jogador na fila.\nClique nos botões abaixo."
    emb.add_field(name="Jogadores", value=txt, inline=False)
    return emb

class FilaView(discord.ui.View):
    def __init__(self, cid, valor):
        super().__init__(timeout=None)
        self.cid=cid; self.valor=valor
    @discord.ui.button(label="Gelo Infinito", style=discord.ButtonStyle.secondary, emoji="🧊")
    async def infinito(self, i, b): await self.entrar(i, "Gelo Infinito")
    @discord.ui.button(label="Gelo Normal", style=discord.ButtonStyle.secondary, emoji="🧊")
    async def normal(self, i, b): await self.entrar(i, "Gelo Normal")
    @discord.ui.button(label="Sair", style=discord.ButtonStyle.red, emoji="🚪")
    async def sair(self, i, b):
        f=get_fila(self.cid, self.valor)
        u=i.user; saiu=False
        for t in f:
            if u in f[t]: f[t].remove(u); saiu=True
        if saiu:
            await i.response.defer(ephemeral=True)
            await atualizar_uma_fila(i.guild.get_channel(self.cid), self.valor)
            await i.followup.send(f"Saiu da {formatar(self.valor)}", ephemeral=True)
        else:
            await i.response.send_message("Você não está nessa fila.", ephemeral=True)
    async def entrar(self, inter, tipo):
        await inter.response.defer(ephemeral=True)
        f=get_fila(self.cid, self.valor)
        u=inter.user
        for t in f:
            if u in f[t]: f[t].remove(u)
        f[tipo].append(u)
        canal=inter.guild.get_channel(self.cid)
        if len(f[tipo]) >= get_qtd(canal.name):
            jog=f[tipo][:get_qtd(canal.name)]; f[tipo]=f[tipo][get_qtd(canal.name):]
            menc=" ".join([j.mention for j in jog])
            await canal.send(content=menc, embed=discord.Embed(title="🔔 PARTIDA ENCONTRADA!", description=f"**Canal:** {canal.mention}\n**Valor:** {formatar(self.valor)}\n**Modo:** {tipo}\n**Jogadores:** {menc}\n\nStaff: `!sala ID SENHA`", color=0x00FF00))
        await atualizar_uma_fila(canal, self.valor)
        await inter.followup.send(f"Entrou: {formatar(self.valor)} - {tipo}", ephemeral=True)

async def atualizar_uma_fila(channel, valor):
    if not channel: return
    emb = build_embed(channel, valor)
    view = FilaView(channel.id, valor)
    async for msg in channel.history(limit=100):
        if msg.author == bot.user and msg.embeds and formatar(valor) in msg.embeds[0].title:
            try:
                await msg.edit(embed=emb, view=view)
                return
            except: pass
    await channel.send(embed=emb, view=view)

async def setup_inicial(channel):
    async for m in channel.history(limit=100):
        if m.author == bot.user:
            try: await m.delete()
            except: pass
    for v in VALORES:
        await channel.send(embed=build_embed(channel, v), view=FilaView(channel.id, v))
        await asyncio.sleep(0.6)

class TicketView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.blurple, emoji="🎫", custom_id="ticket_abrir")
    async def abrir(self, i, b):
        g=i.guild; ov={g.default_role: discord.PermissionOverwrite(view_channel=False), i.user: discord.PermissionOverwrite(view_channel=True, send_messages=True), g.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)}
        cat=discord.utils.get(g.categories, name="Tickets")
        ch=await g.create_text_channel(f"ticket-{i.user.name}", overwrites=ov, category=cat)
        await ch.send(embed=discord.Embed(title="Suporte ORG SLUSH", description=f"{i.user.mention} Explique seu problema! `!fechar`", color=0x00FF00))
        await i.response.send_message(f"Ticket: {ch.mention}", ephemeral=True)

@bot.event
async def on_ready():
    print(f"ON {bot.user}")
    bot.add_view(TicketView())
    for guild in bot.guilds:
        for ch in get_canais_fila(guild):
            for v in VALORES:
                bot.add_view(FilaView(ch.id, v))

@bot.event
async def on_message(m):
    if m.author.bot:
        await bot.process_commands(m); return
    if CANAL_SUPORTE in m.channel.name.lower() and not m.author.guild_permissions.manage_messages:
        try: await m.delete()
        except: pass
        return
    await bot.process_commands(m)

@bot.command()
async def fechar(ctx):
    if "ticket-" in ctx.channel.name:
        await ctx.send("Fechando..."); await asyncio.sleep(2); await ctx.channel.delete()

@bot.command()
async def sala(ctx, id_sala: str, senha: str):
    if ctx.author.guild_permissions.manage_messages:
        await ctx.send("@here", embed=discord.Embed(title="🎮 SALA CRIADA!", description=f"**ID:** `{id_sala}`\n**Senha:** `{senha}`", color=0xFF0000))

@bot.command()
async def setup_tudo(ctx):
    if not ctx.author.guild_permissions.administrator: return
    await ctx.send("Configurando... 20s")
    sup=discord.utils.find(lambda c: CANAL_SUPORTE in c.name.lower(), ctx.guild.text_channels)
    if sup:
        async for x in sup.history(limit=20):
            try: await x.delete()
            except: pass
        await sup.send(embed=discord.Embed(title="📢 SUPORTE ORG SLUSH", description="Clique abaixo para abrir ticket privado.", color=0x2B88D8), view=TicketView())
    for ch in get_canais_fila(ctx.guild):
        await setup_inicial(ch)
    await ctx.send("✅ Pronto! Agora não duplica mais.")

bot.run(TOKEN)
