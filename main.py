import discord, os, re
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")
VALORES = [0.60, 1.00, 2.00, 3.00, 5.00, 7.00, 10.00, 15.00, 20.00, 50.00, 100.00]

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

def get_max_emu(nome):
    qtd = get_qtd_jogadores(nome)
    if qtd == 4: return 1
    if qtd == 6: return 2
    if qtd == 8: return 3
    return 1

def get_fila(cid, valor, nome_canal):
    if cid not in filas: filas[cid] = {}
    if valor not in filas[cid]:
        if "misto" in nome_canal.lower():
            max_emu = get_max_emu(nome_canal)
            filas[cid][valor] = {f"{i} Emu": [] for i in range(1, max_emu+1)}
        else:
            filas[cid][valor] = {"Gelo Infinito": [], "Gelo Normal": []}
    return filas[cid][valor]

def eh_canal_alvo(nome):
    n = nome.lower()
    return "x" in n

def build_embed_fila(channel, valor):
    f = get_fila(channel.id, valor, channel.name)
    titulo = f"{formatar_titulo(channel.name)} • {formatar(valor)}"
    emb = discord.Embed(title=titulo, color=0x00FF88) # RISCO VERDE

    if all(len(v) == 0 for v in f.values()):
        emb.description = f"**Jogadores**\nNenhum jogador na fila."
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

class FilaView(discord.ui.View):
    def __init__(self, valor, cid, nome_canal):
        super().__init__(timeout=None)
        self.valor = valor
        self.cid = cid
        self.nome_canal = nome_canal

        # CRIA BOTÕES DINÂMICOS IGUAL DO VÍDEO
        if "misto" in nome_canal.lower():
            max_emu = get_max_emu(nome_canal)
            for i in range(1, max_emu+1):
                self.add_item(EmuButton(f"{i} Emu", valor, cid, nome_canal))
            self.add_item(SairButton(valor, cid, nome_canal))
        else:
            self.add_item(GeloButton("Gelo Infinito", valor, cid, nome_canal, discord.ButtonStyle.primary))
            self.add_item(GeloButton("Gelo Normal", valor, cid, nome_canal, discord.ButtonStyle.secondary))
            self.add_item(SairButton(valor, cid, nome_canal))

class EmuButton(discord.ui.Button):
    def __init__(self, label, valor, cid, nome_canal):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, emoji="🎮")
        self.valor = valor
        self.cid = cid
        self.nome_canal = nome_canal
        self.tipo = label
    async def callback(self, interaction: discord.Interaction):
        fila = get_fila(self.cid, self.valor, self.nome_canal)
        for t in fila:
            if interaction.user in fila[t]:
                return await interaction.response.send_message(f"❌ Você já está no {t}", ephemeral=True)
        fila[self.tipo].append(interaction.user)
        canal = bot.get_channel(self.cid)
        await interaction.response.defer()
        for msg in [m async for m in canal.history(limit=30)]:
            if msg.author == bot.user and msg.embeds and "Jogadores" in msg.embeds[0].description:
                await msg.edit(embed=build_embed_fila(canal, self.valor), view=FilaView(self.valor, self.cid, self.nome_canal))
                break
        qtd = get_qtd_jogadores(self.nome_canal)
        if len(fila[self.tipo]) >= qtd:
            jogadores = fila[self.tipo][:qtd]
            fila[self.tipo] = fila[self.tipo][qtd:]
            mentions = " ".join([f"<@{u.id}>" for u in jogadores])
            emb = discord.Embed(title=f"Partida {formatar_titulo(canal.name)} - {formatar(self.valor)}", color=0x00FF88, description=f"**{self.tipo}**\n{mentions}")
            await canal.send(content=mentions, embed=emb)
            for msg in [m async for m in canal.history(limit=30)]:
                if msg.author == bot.user and msg.embeds and "Jogadores" in msg.embeds[0].description:
                    await msg.edit(embed=build_embed_fila(canal, self.valor), view=FilaView(self.valor, self.cid, self.nome_canal))
                    break

class GeloButton(discord.ui.Button):
    def __init__(self, label, valor, cid, nome_canal, style):
        super().__init__(label=label, style=style, emoji="🧊")
        self.valor = valor; self.cid = cid; self.nome_canal = nome_canal; self.tipo = label
    async def callback(self, interaction: discord.Interaction):
        fila = get_fila(self.cid, self.valor, self.nome_canal)
        for t in fila:
            if interaction.user in fila[t]:
                return await interaction.response.send_message(f"❌ Já está no {t}", ephemeral=True)
        fila[self.tipo].append(interaction.user)
        canal = bot.get_channel(self.cid)
        await interaction.response.defer()
        for msg in [m async for m in canal.history(limit=30)]:
            if msg.author == bot.user and msg.embeds and "Jogadores" in msg.embeds[0].description:
                await msg.edit(embed=build_embed_fila(canal, self.valor), view=FilaView(self.valor, self.cid, self.nome_canal))
                break
        qtd = get_qtd_jogadores(self.nome_canal)
        if len(fila[self.tipo]) >= qtd:
            jogadores = fila[self.tipo][:qtd]
            fila[self.tipo] = fila[self.tipo][qtd:]
            mentions = " ".join([f"<@{u.id}>" for u in jogadores])
            emb = discord.Embed(title=f"Partida {formatar_titulo(canal.name)}", color=0x00FF88, description=f"**{self.tipo}**\n{mentions}")
            await canal.send(content=mentions, embed=emb)
            for msg in [m async for m in canal.history(limit=30)]:
                if msg.author == bot.user and msg.embeds and "Jogadores" in msg.embeds[0].description:
                    await msg.edit(embed=build_embed_fila(canal, self.valor), view=FilaView(self.valor, self.cid, self.nome_canal))
                    break

class SairButton(discord.ui.Button):
    def __init__(self, valor, cid, nome_canal):
        super().__init__(label="Sair", style=discord.ButtonStyle.danger, emoji="↩️")
        self.valor = valor; self.cid = cid; self.nome_canal = nome_canal
    async def callback(self, interaction: discord.Interaction):
        fila = get_fila(self.cid, self.valor, self.nome_canal)
        saiu=False
        for t in fila:
            if interaction.user in fila[t]:
                fila[t].remove(interaction.user); saiu=True
        if not saiu: return await interaction.response.send_message("❌ Você não está nessa fila", ephemeral=True)
        canal = bot.get_channel(self.cid)
        await interaction.response.defer()
        for msg in [m async for m in canal.history(limit=30)]:
            if msg.author == bot.user and msg.embeds and "Jogadores" in msg.embeds[0].description:
                await msg.edit(embed=build_embed_fila(canal, self.valor), view=FilaView(self.valor, self.cid, self.nome_canal))
                break

@bot.event
async def on_ready(): print(f"ON {bot.user}")

@bot.command()
async def fila(ctx):
    total=0
    for canal in ctx.guild.text_channels:
        if eh_canal_alvo(canal.name):
            for v in VALORES:
                await canal.send(embed=build_embed_fila(canal, v), view=FilaView(v, canal.id, canal.name))
                total+=1
    await ctx.send(f"✅ {total} fileiras criadas!")

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
    await ctx.send(f"✅ Reset {apag} msgs. Use `!fila`")

bot.run(TOKEN)
