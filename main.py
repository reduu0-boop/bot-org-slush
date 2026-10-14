import discord, os, re, asyncio
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")
PIX_KEY = os.getenv("PIX_KEY") or "PIX_NAO_CONFIGURADO"
VALORES = [0.70, 1.00, 2.00, 3.00, 5.00, 7.00, 10.00, 15.00, 20.00, 30.00, 50.00, 100.00, 200.00]
CATEGORIA_PARTIDAS = "PARTIDAS"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
filas = {}
aps = {}

def formatar(v):
    return f"R$ {v:.2f}".replace('.', ',')

def get_taxa(valor):
    return 2.50 if valor >= 30 else 0.50

def formatar_titulo(n):
    n = n.lower().replace("🦔","").replace("•","").strip().replace("-", " ").replace("x", "v")
    return n.title().replace("V", "v")

def get_qtd_jogadores(nome):
    m = re.search(r'(\d+)x\d+', nome.lower())
    return int(m.group(1))*2 if m else 2

def get_max_emu(nome):
    qtd = get_qtd_jogadores(nome)
    if qtd == 4:
        return 1
    if qtd == 6:
        return 2
    if qtd == 8:
        return 3
    return 1

def get_fila(cid, valor, nome_canal):
    if cid not in filas:
        filas[cid] = {}
    if valor not in filas[cid]:
        if "misto" in nome_canal.lower():
            max_emu = get_max_emu(nome_canal)
            filas[cid][valor] = {f"{i} Emu": [] for i in range(1, max_emu+1)}
        else:
            filas[cid][valor] = {"Gelo Infinito": [], "Gelo Normal": []}
    return filas[cid][valor]

def eh_canal_alvo(nome):
    n = nome.lower()
    if "exposed" in n or "suporte" in n or "ticket" in n or "bem-vindo" in n:
        return False
    return bool(re.search(r'\d+x\d+', n))

def build_embed_fila(channel, valor):
    f = get_fila(channel.id, valor, channel.name)
    titulo = f"{formatar_titulo(channel.name)} • {formatar(valor)}"
    emb = discord.Embed(title=titulo, color=0x00FF88)
    if all(len(v) == 0 for v in f.values()):
        emb.description = "**Jogadores**\nNenhum jogador na fila."
    else:
        desc = "**Jogadores**\n"
        for tipo, lista in f.items():
            if lista:
                mentions = " | ".join([f"<@{u.id}>" for u in lista])
                desc += f"{tipo} | {mentions}\n"
        if desc == "**Jogadores**\n":
            desc += "Nenhum jogador na fila."
        emb.description = desc.strip()
    return emb
