import discord
from discord.ext import commands
import os, asyncio, random, re

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# REMOVIDO 0,20 e 0,40
VALORES = [0.70, 1.00, 2.00, 3.00, 5.00, 10.00, 20.00, 30.00, 50.00, 100.00, 200.00]
TAXA_POR_PESSOA = 0.50

filas = {}

def formatar(v): return f"R$ {v:.2f}".replace('.', ',')

def get_qtd_jogadores(nome_canal):
    m = re.search(r'(\d+)x\d+', nome_canal.lower())
    if m:
        return int(m.group(1)) * 2
    return 2

def get_fila(cid, valor):
    if cid not in filas: filas[cid] = {}
    if valor not in filas[cid]: filas[cid][valor] = {"Gelo Infinito": [], "Gelo Normal": []}
    return filas[cid][valor]

def build_embed_fila(channel, valor):
    f = get_fila(channel.id, valor)
    qtd = get_qtd_jogadores(channel.name)
    emb = discord.Embed(title=f"💸 {channel.name.upper()} • {formatar(valor)}", color=0x2B2D31)
    desc = ""
    for tipo in ["Gelo Infinito", "Gelo Normal"]:
        if f[tipo]:
            mentions = " ".join([f"<@{u.id}>" for u in f[tipo]])
            icon = "♾️" if "Infinito" in tipo else "🧊"
            desc += f"{icon} {tipo} ({len(f[tipo])}/{qtd}): {mentions}\n"
    if not desc:
        desc = f"👥 **Jogadores** (0/{qtd})\n`Nenhum jogador na fila.`"
    else:
        desc = f"👥 **Jogadores**\n" + desc
    emb.description = desc
    emb.set_footer(text=f"🦔 {channel.name} • Entrada {formatar(valor)} • Taxa {formatar(TAXA_POR_PESSOA)}/pessoa")
    return emb

def calcular_premio(valor, qtd_jogadores):
    total_mesa = valor * qtd_jogadores
    taxa_total = TAXA_POR_PESSOA * qtd_jogadores
    premio = total_mesa - taxa_total
    return total_mesa, premio, taxa_total

class PartidaView(discord.ui.View):
    def __init__(self, jogadores, valor, canal_origem):
        super().__init__(timeout=600)
        self.jogadores=jogadores; self.valor=valor; self.canal_origem=canal_origem; self.confirmados=set()
    @discord.ui.button(label="Confirmar Partida", style=discord.ButtonStyle.green, emoji="✅")
    async def confirmar(self, inter, btn):
        if inter.user not in self.jogadores: return await inter.response.send_message("❌ Não é sua partida.", ephemeral=True)
        self.confirmados.add(inter.user.id)
        await inter.response.send_message(f"✅ {inter.user.mention} confirmou! ({len(self.confirmados)}/{len(self.jogadores)})")
        if len(self.confirmados)==len(self.jogadores):
            total, premio, taxa = calcular_premio(self.valor, len(self.jogadores))
            emb=discord.Embed(title="✅ PARTIDA CONFIRMADA!", description=f"💰 Mesa: {formatar(total)}\n🏆 Prêmio: {formatar(premio)}\n💵 Taxa org ({len(self.jogadores)}x {formatar(TAXA_POR_PESSOA)}): {formatar(taxa)}\nAguardem: `!sala ID SENHA`", color=0x00FF00)
            await inter.channel.send(content=" ".join([j.mention for j in self.jogadores]), embed=emb)
            self.stop()
    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.red, emoji="❌")
    async def cancelar(self, inter, btn):
        f=get_fila(self.canal_origem.id, self.valor)
        for t in f:
            for u in self.jogadores:
                if u in f[t]: f[t].remove(u)
        await inter.response.send_message("❌ Cancelada.")
        try: await inter.channel.delete()
        except: pass
        self.stop()

class FilaView(discord.ui.View):
    def __init__(self, cid, valor):
        super().__init__(timeout=None); self.cid=cid; self.valor=valor
    @discord.ui.button(label="Gelo Infinito", style=discord.ButtonStyle.secondary, emoji="♾️")
    async def infinito(self, i, b): await self.entrar(i, "Gelo Infinito")
    @discord.ui.button(label="Gelo Normal", style=discord.ButtonStyle.secondary, emoji="🧊")
    async def normal(self, i, b): await self.entrar(i, "Gelo Normal")
    @discord.ui.button(label="Sair", style=discord.ButtonStyle.red, emoji="↩️")
    async def sair(self, i, b):
        f=get_fila(self.cid, self.valor)
        for t in f:
            if i.user in f[t]: f[t].remove(i.user)
        await i.response.defer(ephemeral=True)
        await atualizar_uma_fila(i.guild.get_channel(self.cid), self.valor)
        await i.followup.send("Saiu.", ephemeral=True)
    async def entrar(self, inter, tipo):
        await inter.response.defer(ephemeral=True)
        f=get_fila(self.cid, self.valor)
        canal = inter.guild.get_channel(self.cid)
        qtd_needed = get_qtd_jogadores(canal.name)
        for t in f:
            if inter.user in f[t]: f[t].remove(inter.user)
        f[tipo].append(inter.user)
        if len(f[tipo]) >= qtd_needed:
            jogadores = f[tipo][:qtd_needed]
            f[tipo]=f[tipo][qtd_needed:]
            await atualizar_uma_fila(canal, self.valor)
            await criar_partida(canal, jogadores, self.valor, tipo)
            await inter.followup.send(f"🔥 Partida encontrada! {canal.mention}", ephemeral=True)
        else:
            await atualizar_uma_fila(canal, self.valor)
            await inter.followup.send(f"✅ Entrou: {formatar(self.valor)} - {tipo} ({len(f[tipo])}/{qtd_needed})", ephemeral=True)

async def atualizar_uma_fila(channel, valor):
    if not channel: return
    emb=build_embed_fila(channel, valor)
    view=FilaView(channel.id, valor)
    async for msg in channel.history(limit=200):
        if msg.author==bot.user and msg.embeds and formatar(valor) in msg.embeds[0].title:
            try: await msg.edit(embed=emb, view=view); return
            except: pass
    await channel.send(embed=emb, view=view)

async def criar_partida(canal_origem, jogadores, valor, tipo):
    guild=canal_origem.guild
    total, premio, taxa = calcular_premio(valor, len(jogadores))
    try:
        thread=await canal_origem.create_thread(name=f"partida-{random.randint(35130,35500)}", type=discord.ChannelType.private_thread, auto_archive_duration=60)
        for j in jogadores:
            try: await thread.add_user(j)
            except: pass
        canal=thread
    except:
        overwrites={guild.default_role: discord.PermissionOverwrite(view_channel=False), guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)}
        for j in jogadores: overwrites[j]=discord.PermissionOverwrite(view_channel=True, send_messages=True)
        canal=await guild.create_text_channel(f"partida-{random.randint(35130,35500)}", overwrites=overwrites, category=canal_origem.category)
    lista = "\n".join([f"{i+1}. {j.mention}" for i,j in enumerate(jogadores)])
    emb=discord.Embed(description=f"{' '.join([j.mention for j in jogadores])}\n\n**⏳ Aguardando**\n{canal_origem.name.upper()} {tipo} {formatar(valor)}\n\n**👥 Jogadores**\n{lista}", color=0x2B2D31)
    info=discord.Embed(description=f"💰 **APOSTADO {formatar(valor)}**\n\n🏦 **Mesa:** {formatar(total)} ({len(jogadores)}x {formatar(valor)})\n💵 **Taxa org:** {formatar(taxa)} ({len(jogadores)}x {formatar(TAXA_POR_PESSOA)})\n🏆 **Prêmio vencedor:** {formatar(premio)}\n\n📄 Full Mobile\n⚔️ 1ª Full Desert / Full UMP e XM8", color=0x2B2D31)
    await canal.send(content=" ".join([j.mention for j in jogadores]), embed=emb, view=PartidaView(jogadores, valor, canal_origem))
    await canal.send(embed=info)

def eh_canal_alvo(nome):
    nome=nome.lower()
    if "x" not in nome: return False
    if not any(k in nome for k in ["mobile", "misto", "emulador"]): return False
    return True

@bot.event
async def on_ready():
    print(f"ON {bot.user}")
    for g in bot.guilds:
        for ch in g.text_channels:
            if eh_canal_alvo(ch.name):
                for v in VALORES:
                    bot.add_view(FilaView(ch.id, v))

@bot.command()
async def reset_total(ctx, filtro: str = "x"):
    if not ctx.author.guild_permissions.administrator: return
    filtro=filtro.lower()
    canais_para_resetar=[]
    for ch in ctx.guild.text_channels:
        if not eh_canal_alvo(ch.name): continue
        if filtro=="x": canais_para_resetar.append(ch)
        elif filtro in ch.name.lower(): canais_para_resetar.append(ch)
    if not canais_para_resetar:
        return await ctx.send(f"❌ Nenhum canal com X e filtro `{filtro}`.")
    await ctx.send(f"🧹 Limpando {len(canais_para_resetar)} canais ({filtro.upper()}) - Só os com X...")
    for ch in canais_para_resetar:
        async for m in ch.history(limit=300):
            if m.author==bot.user:
                try: await m.delete()
                except: pass
        for t in ch.threads:
            if "partida-" in t.name:
                try: await t.delete()
                except: pass
    await asyncio.sleep(1)
    for ch in canais_para_resetar:
        for v in sorted(VALORES):
            await ch.send(embed=build_embed_fila(ch, v), view=FilaView(ch.id, v))
            await asyncio.sleep(0.25)
    await ctx.send(f"✅ Pronto! {len(canais_para_resetar)} canais resetados sem R$ 0,20 e R$ 0,40. Taxa: {formatar(TAXA_POR_PESSOA)}/pessoa.")

@bot.command()
async def setup_tudo(ctx, filtro="x"): await reset_total(ctx, filtro)
@bot.command()
async def sala(ctx, id_sala: str, senha: str):
    if ctx.author.guild_permissions.manage_messages:
        await ctx.send(f"@here **🏠 SALA LIBERADA!**\nID: `{id_sala}`\nSENHA: `{senha}`")

bot.run(TOKEN)
