import discord
from discord.ext import commands
import os, asyncio, random

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

VALORES = [2.00, 3.00, 5.00, 5.50, 10.00, 20.00, 30.00, 50.00] # coloca os que você usa
filas = {}
partidas_confirm = {}

def formatar(v): return f"R$ {v:.2f}".replace('.', ',')
def get_fila(cid, valor):
    if cid not in filas: filas[cid] = {}
    if valor not in filas[cid]: filas[cid][valor] = {"Gelo Infinito": [], "Gelo Normal": []}
    return filas[cid][valor]

def build_embed_fila(channel, valor):
    f = get_fila(channel.id, valor)
    emb = discord.Embed(title=f"{channel.name.upper()} • {formatar(valor)}", color=0x2B2D31)
    txt = ""
    for tipo in ["Gelo Normal", "Gelo Infinito"]:
        if f[tipo]:
            txt += f"**Jogadores\n{tipo} | @{f[tipo][0].id if f[tipo] else ''}**\n" if False else f"**Gelo Normal |** " + " ".join([f"<@{u.id}>" for u in f[tipo]]) + "\n"
            # formato do video
            txt = ""
            for t in ["Gelo Normal", "Gelo Infinito"]:
                if f[t]:
                    ids = ", ".join([f"<@{u.id}>" for u in f[t]])
                    txt += f"Gelo Normal | {ids}\n" if "Normal" in t else ""
            if not txt: txt = "Nenhum jogador na fila."
            # vamos refazer certo igual video
    # embed igual video
    emb = discord.Embed(title=f"1v1 Mobile • {formatar(valor)}", color=0x2B2D31)
    f_atual = f
    tem_jog = any(f_atual[t] for t in f_atual)
    if tem_jog:
        # pega o primeiro tipo que tem gente
        for t in f_atual:
            if f_atual[t]:
                mentions = "".join([f"<@{u.id}>" for u in f_atual[t]])
                emb.description = f"Jogadores\n{t} | {mentions}"
                break
    else:
        emb.description = "Jogadores\nNenhum jogador na fila."
    emb.set_footer(text=f"{channel.name}")
    return emb

class PartidaView(discord.ui.View):
    def __init__(self, jogadores, valor, canal_origem):
        super().__init__(timeout=300)
        self.jogadores = jogadores
        self.valor = valor
        self.confirmados = set()
        self.canal_origem = canal_origem

    @discord.ui.button(label="Confirmar Partida", style=discord.ButtonStyle.green, emoji="✅")
    async def confirmar(self, inter, btn):
        if inter.user not in self.jogadores:
            return await inter.response.send_message("Você não é dessa partida.", ephemeral=True)
        self.confirmados.add(inter.user.id)
        await inter.response.send_message(f"{inter.user.mention} confirmou! ({len(self.confirmados)}/{len(self.jogadores)})", ephemeral=False)

        if len(self.confirmados) == len(self.jogadores):
            emb = discord.Embed(title="✅ PARTIDA CONFIRMADA!", description=f"Valor: **{formatar(self.valor)}**\nAguardem staff criar a sala com `!sala ID SENHA`\n\nJogadores: {' '.join([j.mention for j in self.jogadores])}", color=0x00FF00)
            await inter.channel.send(content=" ".join([j.mention for j in self.jogadores]), embed=emb)
            self.stop()

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.red, emoji="❌")
    async def cancelar(self, inter, btn):
        await inter.response.send_message("Partida cancelada.", ephemeral=False)
        # devolve pra fila
        for u in self.jogadores:
            f = get_fila(self.canal_origem.id, self.valor)
            for t in f:
                if u in f[t]: f[t].remove(u)
        try: await inter.channel.delete()
        except: pass
        self.stop()

class FilaView(discord.ui.View):
    def __init__(self, cid, valor):
        super().__init__(timeout=None)
        self.cid=cid; self.valor=valor
        self.custom_id = f"fila_{cid}_{valor}"
    @discord.ui.button(label="Gelo Infinito", style=discord.ButtonStyle.secondary)
    async def infinito(self, i, b): await self.entrar(i, "Gelo Infinito")
    @discord.ui.button(label="Gelo Normal", style=discord.ButtonStyle.secondary)
    async def normal(self, i, b): await self.entrar(i, "Gelo Normal")
    @discord.ui.button(label="Sair", style=discord.ButtonStyle.red, emoji="↩️")
    async def sair(self, i, b):
        f=get_fila(self.cid, self.valor)
        for t in f:
            if i.user in f[t]: f[t].remove(i.user)
        await i.response.defer(ephemeral=True)
        await atualizar_uma_fila(i.guild.get_channel(self.cid), self.valor)
        await i.followup.send("Saiu da fila.", ephemeral=True)

    async def entrar(self, inter, tipo):
        await inter.response.defer(ephemeral=True)
        cid = self.cid
        valor = self.valor
        f=get_fila(cid, valor)
        # tira de outras
        for t in f:
            if inter.user in f[t]: f[t].remove(inter.user)
        f[tipo].append(inter.user)

        canal = inter.guild.get_channel(cid)
        # se completou 2 jogadores
        if len(f[tipo]) >= 2:
            jogadores = f[tipo][:2]
            f[tipo] = f[tipo][2:]
            await atualizar_uma_fila(canal, valor)
            await criar_partida(canal, jogadores, valor, tipo)
            await inter.followup.send(f"Partida encontrada! Vá em {canal.mention}", ephemeral=True)
        else:
            await atualizar_uma_fila(canal, valor)
            await inter.followup.send(f"Entrou na fila {formatar(valor)} - {tipo}", ephemeral=True)

async def atualizar_uma_fila(channel, valor):
    if not channel: return
    emb = build_embed_fila(channel, valor)
    view = FilaView(channel.id, valor)
    async for msg in channel.history(limit=150):
        if msg.author == bot.user and msg.embeds and formatar(valor) in msg.embeds[0].title:
            try:
                await msg.edit(embed=emb, view=view)
                return
            except: pass
    await channel.send(embed=emb, view=view)

async def criar_partida(canal_origem, jogadores, valor, tipo):
    guild = canal_origem.guild
    id_partida = random.randint(35130, 35500)
    nome = f"partida-{id_partida}"

    # Calculo do premio - sobe junto com o preço
    premio_kill = valor  # 1 kill = o valor da entrada
    premio_total = valor * 10 # Booyah + 5 kills = 10x o valor

    try:
        thread = await canal_origem.create_thread(name=nome, type=discord.ChannelType.private_thread, auto_archive_duration=60)
        for j in jogadores:
            try: await thread.add_user(j)
            except: pass
        canal_partida = thread
    except:
        overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
        for j in jogadores: overwrites[j] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        overwrites[guild.me] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        for role in guild.roles:
            if role.permissions.manage_messages:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        canal_partida = await guild.create_text_channel(nome, overwrites=overwrites, category=canal_origem.category)

    embed = discord.Embed(
        description=f"{' '.join([j.mention for j in jogadores])}\n\n**Aguardando**\n1v1 Mobile {tipo} {formatar(valor)}\n\n**Jogadores**\n1. {jogadores[0].mention}\n2. {jogadores[1].mention}", 
        color=0x2B2D31
    )
    embed.set_author(name=f"FUSION 01 APP")

    # AQUI O PREÇO MUDA SOZINHO
    info = discord.Embed(
        description=f"**{formatar(premio_kill)} POR KILL!**\nFazendo o Booyah + 5 kills você já leva **{formatar(premio_total)}** pra casa!\n\n📄 Diário Full Mobile.\n\n**Entre aqui 👇**\nhttps://discord.gg/diariofusion\n\n**REGRA PADRÃO!**\n~ Primeira FULL DESERT\n~ Full ump e xm8",
        color=0x2B2D31
    )

    view = PartidaView(jogadores, valor, canal_origem)
    await canal_partida.send(content=f"{' '.join([j.mention for j in jogadores])}", embed=embed, view=view)
    await canal_partida.send(embed=info)

@bot.event
async def on_ready():
    print(f"ON {bot.user}")
    for g in bot.guilds:
        for ch in g.text_channels:
            if "1x1" in ch.name.lower():
                for v in VALORES:
                    bot.add_view(FilaView(ch.id, v))

@bot.command()
async def setup_tudo(ctx):
    if not ctx.author.guild_permissions.administrator: return
    await ctx.send("Configurando igual do vídeo...")
    for ch in ctx.guild.text_channels:
        if "1x1" in ch.name.lower():
            async for m in ch.history(limit=100):
                if m.author == bot.user:
                    try: await m.delete()
                    except: pass
            for v in VALORES:
                await ch.send(embed=build_embed_fila(ch, v), view=FilaView(ch.id, v))
                await asyncio.sleep(0.5)
    await ctx.send("✅ Pronto! Igual do vídeo da Fusion")

@bot.command()
async def sala(ctx, id_sala: str, senha: str):
    if ctx.author.guild_permissions.manage_messages:
        await ctx.send(f"@here **SALA LIBERADA!**\nID: `{id_sala}`\nSENHA: `{senha}`")

bot.run(TOKEN)
