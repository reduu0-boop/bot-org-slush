import discord
from discord.ext import commands
import os, json, random

TOKEN = os.getenv("DISCORD_TOKEN")
VERDE = 0x00FF7F
ARQ_FILA = "filas.json"

VALORES = ["0,70","1,00","2,00","3,00","4,00","5,00","10,00","30,00","40,00","50,00","100,00","150,00","200,00"]

CANAIS_SLUSH = [
    "🦔・1x1-mobile",
    "🦔・2x2-mobile",
    "🦔・3x3-mobile",
    "🦔・4x4-mobile",
    "🦔・2x2-misto",
    "🦔・3x3-misto",
    "🦔・4x4-misto",
    "🦔・1x1-emulador",
    "🦔・2x2-emulador",
    "🦔・3x3-emulador",
    "🦔・4x4-emulador"
]

def get_taxa(v):
    return 0.50 if v <= 30 else 2.50

def load_json(arq):
    if not os.path.exists(arq): return {}
    try:
        import json; return json.load(open(arq))
    except: return {}
def save_json(arq,data):
    import json; json.dump(data, open(arq,"w"))

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
        if chave not in filas: filas[chave]=[]
        if inter.user.id not in filas[chave]:
            filas[chave].append(inter.user.id)
            save_json(ARQ_FILA, filas)
            await inter.response.send_message(f"Entrou na fila {self.canal_nome} R$ {self.valor_str} ORG SLUSH", ephemeral=True)
            # pega qtd necessária: 1x1=2, 2x2=4, 3x3=6, 4x4=8
            modo = self.canal_nome.split("・")[1].split("-")[0] # 1x1
            q = int(modo[0]) * 2
            if len(filas[chave]) >= q:
                # cria partida
                v=float(self.valor_str.replace(",","."))
                taxa=get_taxa(v)
                total=v+taxa
                premio=v*q
                ch = inter.channel
                emb = discord.Embed(
                    title=f"ORG SLUSH - {self.canal_nome} R$ {self.valor_str}",
                    description=f"AP: R$ {v:.2f}\nTAXA: R$ {taxa:.2f}\nPAGAR: R$ {total:.2f}\nPREMIO: R$ {premio:.2f}",
                    color=VERDE
                )
                await ch.send(f"Partida fechou! {' '.join([f'<@{id}>' for id in filas[chave][:q]])}", embed=emb)
                filas[chave]=filas[chave][q:]
                save_json(ARQ_FILA, filas)
        else:
            await inter.response.send_message("Já está na fila", ephemeral=True)

    @discord.ui.button(label="Sair", style=discord.ButtonStyle.danger)
    async def sair(self, inter, btn):
        filas = load_json(ARQ_FILA)
        chave = f"{self.canal_nome}_{self.valor_str}"
        if chave in filas and inter.user.id in filas[chave]:
            filas[chave].remove(inter.user.id)
            save_json(ARQ_FILA, filas)
        await inter.response.send_message("Saiu", ephemeral=True)

@bot.command()
async def painel_todos(ctx):
    # Use esse comando no canal certo ou ele vai criar em todos de uma vez
    for nome_canal in CANAIS_SLUSH:
        canal = discord.utils.get(ctx.guild.channels, name=nome_canal)
        if not canal:
            continue
        for valor in VALORES:
            v=float(valor.replace(",","."))
            taxa=get_taxa(v)
            emb=discord.Embed(
                title=f"{nome_canal} - R$ {valor}",
                description=f"Jogadores: Nenhum na fila\n\n💸 Pagar: R$ {v+taxa:.2f} (AP R$ {v:.2f} + Taxa R$ {taxa:.2f})\n🏆 Premio total: R$ {v*2:.2f} por time vencedor\n🦔 ORG SLUSH",
                color=VERDE
            )
            await canal.send(embed=emb, view=FilaView(nome_canal, valor))

@bot.command()
async def painel_aqui(ctx):
    # Cria só no canal onde você digitou
    nome_canal = ctx.channel.name
    for valor in VALORES:
        v=float(valor.replace(",","."))
        taxa=get_taxa(v)
        emb=discord.Embed(
            title=f"{nome_canal} - R$ {valor}",
            description=f"Jogadores: Nenhum na fila\n\n💸 Pagar: R$ {v+taxa:.2f}\n🏆 Ganha: R$ {v*2:.2f}\nTaxa ORG SLUSH: R$ {taxa:.2f}",
            color=VERDE
        )
        await ctx.send(embed=emb, view=FilaView(nome_canal, valor))

@bot.event
async def on_ready():
    print(f"ORG SLUSH VERDE ON")

bot.run(TOKEN)
