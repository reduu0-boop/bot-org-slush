import discord, os, re, asyncio
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")
VALORES = [0.70, 1.00, 2.00, 3.00, 5.00, 7.00, 10.00, 15.00, 20.00, 50.00, 100.00, 200.00]
TAXA_FIXA = 0.50
PIX_KEY = "c2d13650-0370-42e3-a918-0cc68c457646"
CATEGORIA_PARTIDAS = "PARTIDAS"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
filas = {}

def formatar(v): return f"R$ {v:.2f}".replace('.', ',')
def formatar_titulo(n):
    n = n.lower().replace("🦔","").replace("•","").strip().replace("-", " ").replace("x", "v")
    return n.title().replace("V", "v")
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
def eh_canal_alvo(nome): return "x" in nome.lower()

def build_embed_fila(channel, valor):
    f = get_fila(channel.id, valor, channel.name)
    titulo = f"{formatar_titulo(channel.name)} • {formatar(valor)}"
    emb = discord.Embed(title=titulo, color=0x00FF88)
    if all(len(v) == 0 for v in f.values()):
        emb.description = f"**Jogadores**\nNenhum jogador na fila."
    else:
        desc = "**Jogadores**\n"
        for tipo, lista in f.items():
            if lista:
                mentions = " | ".join([f"<@{u.id}>" for u in lista])
                desc += f"{tipo} | {mentions}\n"
        if desc == "**Jogadores**\n": desc += "Nenhum jogador na fila."
        emb.description = desc.strip()
    return emb

# CORREÇÃO DO BUG DO R$ 50 DUPLICADO
async def achar_e_editar(canal, valor, nome_canal):
    alvo = formatar(valor)
    async for msg in canal.history(limit=150):
        if msg.author == bot.user and msg.embeds:
            embed = msg.embeds[0]
            if alvo in embed.title and "Jogadores" in embed.description:
                try:
                    await msg.edit(embed=build_embed_fila(canal, valor), view=FilaView(valor, canal.id, nome_canal))
                    return True
                except: pass
    return False

async def criar_canal_partida(guild, jogadores, valor, tipo_fila, canal_origem_nome):
    categoria = discord.utils.get(guild.categories, name=CATEGORIA_PARTIDAS)
    if not categoria:
        categoria = await guild.create_category(CATEGORIA_PARTIDAS)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
    }
    for jogador in jogadores:
        overwrites[jogador] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

    total = valor + TAXA_FIXA
    nome_canal_priv = f"ap-{formatar(valor).replace('R$ ','').replace(',','-')}-{tipo_fila.lower().replace(' ','')}-{jogadores[0].name[:5]}".lower()[:30]

    canal_priv = await guild.create_text_channel(nome_canal_priv, category=categoria, overwrites=overwrites)

    emb = discord.Embed(
        title=f"💰 Partida Criada - {formatar_titulo(canal_origem_nome)}",
        color=0x00FF88,
        description=(
            f"**Valor do AP:** {formatar(valor)}\n"
            f"**Taxa:** {formatar(TAXA_FIXA)}\n"
            f"**Total a pagar:** **{formatar(total)}**\n"
            f"**PIX:** `{PIX_KEY}`\n\n"
            f"**Tipo:** {tipo_fila}\n"
            f"**Jogadores:** {' '.join([f'<@{j.id}>' for j in jogadores])}\n\n"
            f"Copia a chave pix e pague para liberar! 🎮"
        )
    )
    view = FecharView()
    mentions = " ".join([f"<@{j.id}>" for j in jogadores])
    await canal_priv.send(content=f"{mentions} sua partida começou!", embed=emb, view=view)
    return canal_priv

class FecharView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Fechar Partida", style=discord.ButtonStyle.danger, emoji="🔒")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Fechando em 5s...")
        await asyncio.sleep(5)
        try: await interaction.channel.delete()
        except: pass

class FilaView(discord.ui.View):
    def __init__(self, valor, cid, nome_canal):
        super().__init__(timeout=None)
        self.valor = valor; self.cid = cid; self.nome_canal = nome_canal
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
        self.valor=valor; self.cid=cid; self.nome_canal=nome_canal; self.tipo=label
    async def callback(self, interaction: discord.Interaction):
        fila = get_fila(self.cid, self.valor, self.nome_canal)
        for t in fila:
            if interaction.user in fila[t]:
                return await interaction.response.send_message(f"❌ Já está no {t}", ephemeral=True)
        fila[self.tipo].append(interaction.user)
        canal = bot.get_channel(self.cid)
        await interaction.response.defer()
        await achar_e_editar(canal, self.valor, self.nome_canal)
        qtd = get_qtd_jogadores(self.nome_canal)
        if len(fila[self.tipo]) >= qtd:
            jogadores = fila[self.tipo][:qtd]
            fila[self.tipo] = fila[self.tipo][qtd:]
            await criar_canal_partida(interaction.guild, jogadores, self.valor, self.tipo, self.nome_canal)
            await achar_e_editar(canal, self.valor, self.nome_canal)

class GeloButton(discord.ui.Button):
    def __init__(self, label, valor, cid, nome_canal, style):
        super().__init__(label=label, style=style, emoji="🧊")
        self.valor=valor; self.cid=cid; self.nome_canal=nome_canal; self.tipo=label
    async def callback(self, interaction: discord.Interaction):
        fila = get_fila(self.cid, self.valor, self.nome_canal)
        for t in fila:
            if interaction.user in fila[t]:
                return await interaction.response.send_message(f"❌ Já está no {t}", ephemeral=True)
        fila[self.tipo].append(interaction.user)
        canal = bot.get_channel(self.cid)
        await interaction.response.defer()
        await achar_e_editar(canal, self.valor, self.nome_canal)
        qtd = get_qtd_jogadores(self.nome_canal)
        if len(fila[self.tipo]) >= qtd:
            jogadores = fila[self.tipo][:qtd]
            fila[self.tipo] = fila[self.tipo][qtd:]
            await criar_canal_partida(interaction.guild, jogadores, self.valor, self.tipo, self.nome_canal)
            await achar_e_editar(canal, self.valor, self.nome_canal)

class SairButton(discord.ui.Button):
    def __init__(self, valor, cid, nome_canal):
        super().__init__(label="Sair", style=discord.ButtonStyle.danger, emoji="↩️")
        self.valor=valor; self.cid=cid; self.nome_canal=nome_canal
    async def callback(self, interaction: discord.Interaction):
        fila = get_fila(self.cid, self.valor, self.nome_canal)
        saiu=False
        for t in fila:
            if interaction.user in fila[t]:
                fila[t].remove(interaction.user); saiu=True
        if not saiu: return await interaction.response.send_message("❌ Você não está nessa fila", ephemeral=True)
        canal = bot.get_channel(self.cid)
        await interaction.response.defer()
        await achar_e_editar(canal, self.valor, self.nome_canal)

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
    await ctx.send(f"✅ {total} fileiras!")
@bot.command()
async def reset_total(ctx):
    if not ctx.author.guild_permissions.administrator: return
    apag=0
    for canal in ctx.guild.text_channels:
        if eh_canal_alvo(canal.name):
            async for msg in canal.history(limit=200):
                if msg.author == bot.user:
                    try: await msg.delete(); apag+=1
                    except: pass
            filas.pop(canal.id, None)
    await ctx.send(f"✅ Reset {apag} msgs. Use `!fila`")
bot.run(TOKEN)
