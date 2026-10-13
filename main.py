import discord
from discord.ext import commands
import os, asyncio, random

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# VALORES DO MENOR PRO MAIOR
VALORES = [0.20, 0.40, 0.70, 1.00, 2.00, 3.00, 5.00, 10.00, 20.00, 30.00, 50.00, 100.00, 200.00]
TAXA_ORG = 0.50 # R$ 0,50 FIXO PRA ORG

filas = {}

def formatar(v):
    return f"R$ {v:.2f}".replace('.', ',')

def get_fila(cid, valor):
    if cid not in filas:
        filas[cid] = {}
    if valor not in filas[cid]:
        filas[cid][valor] = {"Gelo Infinito": [], "Gelo Normal": []}
    return filas[cid][valor]

def build_embed_fila(channel, valor):
    f = get_fila(channel.id, valor)
    emb = discord.Embed(
        title=f"💸 1v1 • {formatar(valor)}",
        color=0x2B2D31
    )
    desc = ""
    for tipo in ["Gelo Infinito", "Gelo Normal"]:
        if f[tipo]:
            mentions = " ".join([f"<@{u.id}>" for u in f[tipo]])
            icon = "♾️" if "Infinito" in tipo else "🧊"
            desc += f"{icon} {tipo}: {mentions}\n"

    if not desc:
        desc = "👥 **Jogadores**\n`Nenhum jogador na fila.`"
    else:
        desc = "👥 **Jogadores**\n" + desc

    emb.description = desc
    emb.set_footer(text=f"🦔 {channel.name} • Entrada {formatar(valor)}")
    return emb

def calcular_premio(valor, qtd_jogadores=2):
    total_mesa = valor * qtd_jogadores
    if total_mesa <= 1.00:
        # Não cobra taxa em valores muito baixos pra não ficar negativo
        premio = total_mesa
        taxa = 0
    else:
        premio = total_mesa - TAXA_ORG
        taxa = TAXA_ORG
    return total_mesa, premio, taxa

class PartidaView(discord.ui.View):
    def __init__(self, jogadores, valor, canal_origem):
        super().__init__(timeout=600)
        self.jogadores = jogadores
        self.valor = valor
        self.canal_origem = canal_origem
        self.confirmados = set()

    @discord.ui.button(label="Confirmar Partida", style=discord.ButtonStyle.green, emoji="✅")
    async def confirmar(self, inter, btn):
        if inter.user not in self.jogadores:
            return await inter.response.send_message("❌ Essa não é sua partida.", ephemeral=True)
        self.confirmados.add(inter.user.id)
        await inter.response.send_message(f"✅ {inter.user.mention} confirmou! ({len(self.confirmados)}/{len(self.jogadores)})")
        if len(self.confirmados) == len(self.jogadores):
            total_mesa, premio, taxa = calcular_premio(self.valor, len(self.jogadores))
            emb = discord.Embed(
                title="✅ PARTIDA CONFIRMADA!",
                description=f"💰 **Mesa:** {formatar(total_mesa)}\n🏆 **Prêmio:** {formatar(premio)}\n\nAguardem staff: `!sala ID SENHA`",
                color=0x00FF00
            )
            await inter.channel.send(content=" ".join([j.mention for j in self.jogadores]), embed=emb)
            self.stop()

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.red, emoji="❌")
    async def cancelar(self, inter, btn):
        f = get_fila(self.canal_origem.id, self.valor)
        for t in f:
            for u in self.jogadores:
                if u in f[t]:
                    f[t].remove(u)
        await inter.response.send_message("❌ Partida cancelada.")
        try:
            await inter.channel.delete()
        except:
            pass
        self.stop()

class FilaView(discord.ui.View):
    def __init__(self, cid, valor):
        super().__init__(timeout=None)
        self.cid = cid
        self.valor = valor

    @discord.ui.button(label="Gelo Infinito", style=discord.ButtonStyle.secondary, emoji="♾️")
    async def infinito(self, i, b):
        await self.entrar(i, "Gelo Infinito")

    @discord.ui.button(label="Gelo Normal", style=discord.ButtonStyle.secondary, emoji="🧊")
    async def normal(self, i, b):
        await self.entrar(i, "Gelo Normal")

    @discord.ui.button(label="Sair", style=discord.ButtonStyle.red, emoji="↩️")
    async def sair(self, i, b):
        f = get_fila(self.cid, self.valor)
        for t in f:
            if i.user in f[t]:
                f[t].remove(i.user)
        await i.response.defer(ephemeral=True)
        await atualizar_uma_fila(i.guild.get_channel(self.cid), self.valor)
        await i.followup.send("Saiu da fila.", ephemeral=True)

    async def entrar(self, inter, tipo):
        await inter.response.defer(ephemeral=True)
        f = get_fila(self.cid, self.valor)
        for t in f:
            if inter.user in f[t]:
                f[t].remove(inter.user)
        f[tipo].append(inter.user)
        canal = inter.guild.get_channel(self.cid)
        if len(f[tipo]) >= 2:
            jogadores = f[tipo][:2]
            f[tipo] = f[tipo][2:]
            await atualizar_uma_fila(canal, self.valor)
            await criar_partida(canal, jogadores, self.valor, tipo)
            await inter.followup.send(f"🔥 Partida encontrada! {canal.mention}", ephemeral=True)
        else:
            await atualizar_uma_fila(canal, self.valor)
            await inter.followup.send(f"✅ Entrou: {formatar(self.valor)} - {tipo}", ephemeral=True)

async def atualizar_uma_fila(channel, valor):
    if not channel:
        return
    emb = build_embed_fila(channel, valor)
    view = FilaView(channel.id, valor)
    async for msg in channel.history(limit=200):
        if msg.author == bot.user and msg.embeds and formatar(valor) in msg.embeds[0].title:
            try:
                await msg.edit(embed=emb, view=view)
                return
            except:
                pass
    await channel.send(embed=emb, view=view)

async def criar_partida(canal_origem, jogadores, valor, tipo):
    guild = canal_origem.guild
    total_mesa, premio, taxa = calcular_premio(valor, len(jogadores))

    try:
        thread = await canal_origem.create_thread(
            name=f"partida-{random.randint(35130,35500)}",
            type=discord.ChannelType.private_thread,
            auto_archive_duration=60
        )
        for j in jogadores:
            try:
                await thread.add_user(j)
            except:
                pass
        canal = thread
    except:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        for j in jogadores:
            overwrites[j] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        canal = await guild.create_text_channel(
            f"partida-{random.randint(35130,35500)}",
            overwrites=overwrites,
            category=canal_origem.category
        )

    emb = discord.Embed(
        description=f"{' '.join([j.mention for j in jogadores])}\n\n**⏳ Aguardando**\n1v1 Mobile {tipo} {formatar(valor)}\n\n**👥 Jogadores**\n1. {jogadores[0].mention}\n2. {jogadores[1].mention}",
        color=0x2B2D31
    )

    if taxa == 0:
        taxa_txt = "Isento (valor baixo)"
    else:
        taxa_txt = formatar(taxa)

    info = discord.Embed(
        description=f"💰 **APOSTADO {formatar(valor)}**\n\n"
                    f"🏦 **Mesa:** {formatar(total_mesa)}\n"
                    f"🏆 **Prêmio pro vencedor:** {formatar(premio)}\n"
                    f"💵 **Taxa org:** {taxa_txt}\n\n"
                    f"📄 Diário Full Mobile\n\n"
                    f"**⚔️ REGRA PADRÃO**\n"
                    f"~ 1ª Full Desert\n"
                    f"~ Full UMP e XM8",
        color=0x2B2D31
    )

    await canal.send(content=" ".join([j.mention for j in jogadores]), embed=emb, view=PartidaView(jogadores, valor, canal_origem))
    await canal.send(embed=info)

@bot.event
async def on_ready():
    print(f"ON {bot.user}")
    for g in bot.guilds:
        for ch in g.text_channels:
            if "1x1" in ch.name.lower():
                for v in VALORES:
                    bot.add_view(FilaView(ch.id, v))

@bot.command()
async def reset_total(ctx):
    if not ctx.author.guild_permissions.administrator:
        return
    await ctx.send("🧹 **Resetando tudo...**")
    for ch in ctx.guild.text_channels:
        if "1x1" in ch.name.lower():
            async for m in ch.history(limit=200):
                if m.author == bot.user:
                    try:
                        await m.delete()
                    except:
                        pass
            for t in ch.threads:
                if "partida-" in t.name:
                    try:
                        await t.delete()
                    except:
                        pass
    await asyncio.sleep(1)
    for ch in ctx.guild.text_channels:
        if "1x1" in ch.name.lower():
            for v in sorted(VALORES):
                await ch.send(embed=build_embed_fila(ch, v), view=FilaView(ch.id, v))
                await asyncio.sleep(0.3)
    await ctx.send("✅ **Pronto! Taxa fixa de R$ 0,50 e filas do menor pro maior com emoji.**")

@bot.command()
async def setup_tudo(ctx):
    await reset_total(ctx)

@bot.command()
async def sala(ctx, id_sala: str, senha: str):
    if ctx.author.guild_permissions.manage_messages:
        await ctx.send(f"@here **🏠 SALA LIBERADA!**\nID: `{id_sala}`\nSENHA: `{senha}`")

bot.run(TOKEN)
