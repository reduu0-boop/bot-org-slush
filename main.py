import discord, os, re
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")
VALORES = [0.60, 0.70, 1.00, 2.00, 3.00, 5.00, 10.00, 20.00, 30.00, 50.00, 100.00, 200.00]

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
filas = {}

def formatar(v): return f"R$ {v:.2f}".replace('.', ',')

def formatar_titulo(nome_canal):
    nome = nome_canal.lower().replace("🦔","").replace("•","").strip().replace("-", " ").replace("x", "v")
    return nome.title().replace("V", "v")

def get_qtd_jogadores(nome):
    m = re.search(r'(\d+)x\d+', nome.lower())
    return int(m.group(1))*2 if m else 2

def get_fila(cid, valor):
    if cid not in filas: filas[cid] = {}
    if valor not in filas[cid]: filas[cid][valor] = {"Gelo Infinito": [], "Gelo Normal": []}
    return filas[cid][valor]

def eh_canal_alvo(nome):
    n = nome.lower()
    return "x" in n and any(k in n for k in ["mobile", "misto", "emulador", "emu", "1x1", "2x2", "3x3", "4x4"])

def build_embed_fila(channel, valor):
    f = get_fila(channel.id, valor)
    titulo = f"{formatar_titulo(channel.name)} • {formatar(valor)}"
    emb = discord.Embed(title=titulo, color=0x00FF88) # RISCO VERDE
    if all(len(v) == 0 for v in f.values()):
        emb.description = f"**Jogadores**\nNenhum jogador na fila."
    else:
        desc = "**Jogadores**\n"
        for tipo in ["Gelo Infinito", "Gelo Normal"]:
            if f[tipo]:
                mentions = " | ".join([f"<@{u.id}>" for u in f[tipo]])
                desc += f"{tipo} | {mentions}\n"
            else:
                desc += f"{tipo} | \n"
        emb.description = desc.strip()
    return emb

class FilaView(discord.ui.View):
    def __init__(self, valor, cid):
        super().__init__(timeout=None)
        self.valor = valor
        self.cid = cid
    async def entrar(self, interaction, tipo):
        fila = get_fila(self.cid, self.valor)
        for t in fila:
            if interaction.user in fila[t]:
                return await interaction.response.send_message(f"❌ Você já está no {t}", ephemeral=True)
        fila[tipo].append(interaction.user)
        canal = bot.get_channel(self.cid)
        await interaction.response.defer()
        for msg in [m async for m in canal.history(limit=30)]:
            if msg.author == bot.user and msg.embeds and "Jogadores" in msg.embeds[0].description:
                await msg.edit(embed=build_embed_fila(canal, self.valor), view=FilaView(self.valor, self.cid))
                break
        qtd = get_qtd_jogadores(canal.name)
        if len(fila[tipo]) >= qtd:
            jogadores = fila[tipo][:qtd]
            fila[tipo] = fila[tipo][qtd:]
            mentions = " ".join([f"<@{u.id}>" for u in jogadores])
            emb = discord.Embed(title=f"Partida {formatar_titulo(canal.name)} - {formatar(self.valor)}", color=0x00FF88, description=f"**{tipo}**\n{mentions}")
            await canal.send(content=mentions, embed=emb)
            for msg in [m async for m in canal.history(limit=30)]:
                if msg.author == bot.user and msg.embeds and "Jogadores" in msg.embeds[0].description:
                    await msg.edit(embed=build_embed_fila(canal, self.valor), view=FilaView(self.valor, self.cid))
                    break
    @discord.ui.button(label="Gelo Infinito", emoji="🧊", style=discord.ButtonStyle.primary)
    async def b1(self, i, b): await self.entrar(i, "Gelo Infinito")
    @discord.ui.button(label="Gelo Normal", emoji="🧊", style=discord.ButtonStyle.secondary)
    async def b2(self, i, b): await self.entrar(i, "Gelo Normal")
    @discord.ui.button(label="Sair", emoji="🚪", style=discord.ButtonStyle.danger)
    async def b3(self, i, b):
        fila = get_fila(self.cid, self.valor)
        saiu=False
        for t in fila:
            if i.user in fila[t]:
                fila[t].remove(i.user); saiu=True
        if not saiu: return await i.response.send_message("❌ Você não está nessa fila", ephemeral=True)
        canal = bot.get_channel(self.cid)
        await i.response.defer()
        for msg in [m async for m in canal.history(limit=30)]:
            if msg.author == bot.user and msg.embeds and "Jogadores" in msg.embeds[0].description:
                await msg.edit(embed=build_embed_fila(canal, self.valor), view=FilaView(self.valor, self.cid))
                break

@bot.event
async def on_ready(): print(f"ON {bot.user}")

@bot.command()
async def fila(ctx):
    # Cria em TODOS os canais de AP de uma vez
    total = 0
    for canal in ctx.guild.text_channels:
        if eh_canal_alvo(canal.name):
            for v in VALORES:
                await canal.send(embed=build_embed_fila(canal, v), view=FilaView(v, canal.id))
                total += 1
    await ctx.send(f"✅ Criei {total} fileiras em todos os canais!")

@bot.command()
async def reset_total(ctx):
    if not ctx.author.guild_permissions.administrator: return
    apag=0
    for canal in ctx.guild.text_channels:
        if eh_canal_alvo(canal.name):
            async for msg in canal.history(limit=100):
                if msg.author == bot.user:
                    try: await msg.delete(); apag+=1
                    except: pass
            filas.pop(canal.id, None)
    await ctx.send(f"✅ Reset {apag} mensagens de todos os canais. Agora use `!fila`")

bot.run(TOKEN)
