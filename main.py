import discord, os, re
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")
CHAVE_PIX = "c2d13650-0370-42e3-a918-0cc68c457646"
VALORES = [0.70, 1.00, 2.00, 3.00, 5.00, 10.00, 20.00, 30.00, 50.00, 100.00, 200.00]

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
filas = {}

def formatar(v): return f"R$ {v:.2f}".replace('.', ',')

def get_qtd_jogadores(nome):
    m = re.search(r'(\d+)x\d+', nome.lower())
    return int(m.group(1))*2 if m else 2

def get_fila(cid, valor):
    if cid not in filas: filas[cid] = {}
    if valor not in filas[cid]: filas[cid][valor] = {"Gelo Infinito": [], "Gelo Normal": []}
    return filas[cid][valor]

def calcular_premio(valor, qtd):
    taxa_pp = 2.50 if valor >= 30 else 0.50
    taxa_total = taxa_pp * qtd
    premio = valor * qtd
    total = premio + taxa_total
    return total, premio, taxa_total, taxa_pp

def eh_canal_alvo(nome):
    n = nome.lower()
    return "x" in n and any(k in n for k in ["mobile", "misto", "emulador", "emu", "1x1", "2x2", "4x4"])

def build_embed_fila(channel, valor):
    f = get_fila(channel.id, valor)
    qtd = get_qtd_jogadores(channel.name)
    total, premio, taxa_total, taxa_pp = calcular_premio(valor, qtd)

    emb = discord.Embed(color=0x2B2D31)
    emb.title = f"💸🦔 • {channel.name.upper()} • {formatar(valor)}"

    count = sum(len(f[t]) for t in f)
    if count == 0:
        jogadores_part = f"👥 **Jogadores (0/{qtd})**\n`Nenhum jogador na fila.`"
    else:
        jogadores_part = f"👥 **Jogadores ({count}/{qtd})**\n"
        for tipo in ["Gelo Infinito", "Gelo Normal"]:
            if f[tipo]:
                mentions = " ".join([f"<@{u.id}>" for u in f[tipo]])
                jogadores_part += f"🧊 {tipo}: {mentions}\n"

    emb.description = (
        f"💵 Taxa: {formatar(taxa_pp)} por pessoa\n\n"
        f"{jogadores_part}\n"
        f"💰 **Premiação**\n"
        f"Prêmio: {formatar(premio)}\n"
        f"Taxa Org total: {formatar(taxa_total)}\n\n"
        f"🔑 **Pix**\n"
        f"`{CHAVE_PIX}`"
    )
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
        for msg in [m async for m in canal.history(limit=20)]:
            if msg.author == bot.user and msg.embeds and "Jogadores" in msg.embeds[0].description:
                await msg.edit(embed=build_embed_fila(canal, self.valor), view=FilaView(self.valor, self.cid))
                break
        qtd = get_qtd_jogadores(canal.name)
        if len(fila[tipo]) >= qtd:
            jogadores = fila[tipo][:qtd]
            fila[tipo] = fila[tipo][qtd:]
            total, premio, taxa_total, taxa_pp = calcular_premio(self.valor, len(jogadores))
            mentions = " ".join([f"<@{u.id}>" for u in jogadores])
            emb = discord.Embed(title=f"🎮 Partida - {canal.name}", color=0x00FF88, description=f"**{tipo} - {formatar(self.valor)}**\nPrêmio: {formatar(premio)}\n{mentions}")
            await canal.send(content=mentions, embed=emb)

    @discord.ui.button(label="Gelo Infinito", emoji="🧊", style=discord.ButtonStyle.primary)
    async def b1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.entrar(interaction, "Gelo Infinito")

    @discord.ui.button(label="Gelo Normal", emoji="🧊", style=discord.ButtonStyle.secondary)
    async def b2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.entrar(interaction, "Gelo Normal")

    @discord.ui.button(label="Sair do AP", emoji="❌", style=discord.ButtonStyle.danger)
    async def b3(self, interaction: discord.Interaction, button: discord.ui.Button):
        fila = get_fila(self.cid, self.valor)
        saiu = False
        for t in fila:
            if interaction.user in fila[t]:
                fila[t].remove(interaction.user)
                saiu = True
        if not saiu:
            return await interaction.response.send_message("❌ Você não está em nenhuma fila desse AP", ephemeral=True)

        canal = bot.get_channel(self.cid)
        await interaction.response.defer()
        for msg in [m async for m in canal.history(limit=20)]:
            if msg.author == bot.user and msg.embeds and "Jogadores" in msg.embeds[0].description:
                await msg.edit(embed=build_embed_fila(canal, self.valor), view=FilaView(self.valor, self.cid))
                break
        await interaction.followup.send("✅ Você saiu da fila", ephemeral=True)

@bot.event
async def on_ready(): print(f"ON {bot.user}")

@bot.command()
async def fila(ctx, valor: float = None):
    if valor is None:
        for v in VALORES:
            if eh_canal_alvo(ctx.channel.name):
                await ctx.channel.send(embed=build_embed_fila(ctx.channel, v), view=FilaView(v, ctx.channel.id))
        return
    await ctx.send(embed=build_embed_fila(ctx.channel, valor), view=FilaView(valor, ctx.channel.id))

@bot.command()
async def reset_total(ctx, filtro="x"):
    if not ctx.author.guild_permissions.administrator: return
    apag=0
    for canal in ctx.guild.text_channels:
        if filtro.lower() in canal.name.lower() and eh_canal_alvo(canal.name):
            async for msg in canal.history(limit=100):
                if msg.author == bot.user:
                    try: await msg.delete(); apag+=1
                    except: pass
            filas.pop(canal.id, None)
    await ctx.send(f"✅ Reset {apag} mensagens. Use `!fila` para recriar.")

bot.run(TOKEN)
