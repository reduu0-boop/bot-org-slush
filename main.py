import discord
from discord.ext import commands
import os, json

TOKEN = os.getenv("DISCORD_TOKEN")
VERDE = 0x00FF7F
ARQ_FILA = "filas.json"

VALORES = ["0,70","1,00","2,00","3,00","4,00","5,00","10,00","30,00","40,00","50,00","100,00","150,00","200,00"]

CANAIS_SLUSH = [
    "🦔・1x1-mobile","🦔・2x2-mobile","🦔・3x3-mobile","🦔・4x4-mobile",
    "🦔・2x2-misto","🦔・3x3-misto","🦔・4x4-misto",
    "🦔・1x1-emulador","🦔・2x2-emulador","🦔・3x3-emulador","🦔・4x4-emulador"
]

def load_json(a):
    if not os.path.exists(a): return {}
    try: return json.load(open(a))
    except: return {}
def save_json(a,d): json.dump(d, open(a,"w"))

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

class FilaView(discord.ui.View):
    def __init__(self, canal_nome, valor_str):
        super().__init__(timeout=None)
        self.canal_nome = canal_nome
        self.valor_str = valor_str
    @discord.ui.button(label="Entrar", style=discord.ButtonStyle.success)
    async def entrar(self, inter, btn):
        filas = load_json(ARQ_FILA)
        chave = f"{self.canal_nome}_{self.valor_str}"
        filas.setdefault(chave, [])
        if inter.user.id not in filas[chave]:
            filas[chave].append(inter.user.id)
            save_json(ARQ_FILA, filas)
        await inter.response.send_message("Entrou na fila", ephemeral=True)
    @discord.ui.button(label="Sair", style=discord.ButtonStyle.danger)
    async def sair(self, inter, btn):
        filas = load_json(ARQ_FILA)
        chave = f"{self.canal_nome}_{self.valor_str}"
        if chave in filas and inter.user.id in filas[chave]:
            filas[chave].remove(inter.user.id)
            save_json(ARQ_FILA, filas)
        await inter.response.send_message("Saiu da fila", ephemeral=True)

@bot.command()
async def painel_todos(ctx):
    for nome_canal in CANAIS_SLUSH:
        canal = discord.utils.get(ctx.guild.channels, name=nome_canal)
        if not canal: continue
        for valor in VALORES:
            emb = discord.Embed(
                title=f"• {nome_canal.split('・')[1]} - R$ {valor}",
                description="Jogadores: Nenhum na fila",
                color=VERDE
            )
            await canal.send(embed=emb, view=FilaView(nome_canal, valor))

@bot.command()
async def painel_aqui(ctx):
    nome_canal = ctx.channel.name
    for valor in VALORES:
        emb = discord.Embed(
            title=f"• {nome_canal.split('・')[1]} - R$ {valor}",
            description="Jogadores: Nenhum na fila",
            color=VERDE
        )
        await ctx.send(embed=emb, view=FilaView(nome_canal, valor))

@bot.command()
@commands.has_permissions(manage_messages=True)
async def limpar(ctx):
    await ctx.channel.purge(limit=100)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def limpar_todos(ctx):
    for nome_canal in CANAIS_SLUSH:
        canal = discord.utils.get(ctx.guild.channels, name=nome_canal)
        if canal:
            try: await canal.purge(limit=100)
            except: pass

@bot.event
async def on_ready(): print(f"ORG SLUSH LIMPO ON - {bot.user}")

bot.run(TOKEN)
