import discord, os, re
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")

TAXA_POR_PESSOA = 0.50
VALORES = [0.70, 1.00, 2.00, 3.00, 5.00, 10.00, 20.00, 30.00, 50.00, 100.00, 200.00]
CHAVE_PIX = "c2d13650-0370-42e3-a918-0cc68c457646"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

filas = {}

def formatar(v): return f"R$ {v:.2f}".replace('.', ',')

def get_qtd_jogadores(nome_canal):
    m = re.search(r'(\d+)x\d+', nome_canal.lower())
    if m: return int(m.group(1)) * 2
    return 2

def get_fila(cid, valor):
    if cid not in filas: filas[cid] = {}
    if valor not in filas[cid]: filas[cid][valor] = {"Gelo Infinito": [], "Gelo Normal": []}
    return filas[cid][valor]

def calcular_premio(valor, qtd):
    if valor >= 30:
        taxa = 2.50
    else:
        taxa = TAXA_POR_PESSOA * qtd
    total = valor * qtd
    premio = total - taxa
    return total, premio, taxa

def eh_canal_alvo(nome):
    nome = nome.lower()
    if "x" not in nome: return False
    if not any(k in nome for k in ["mobile", "misto", "emulador", "emu"]): return False
    return True

def build_embed_fila(channel, valor):
    f = get_fila(channel.id, valor)
    qtd = get_qtd_jogadores(channel.name)
    emb = discord.Embed(title=f"💸 {channel.name.upper()} • {formatar(valor)}", color=0xFF7A00)
    desc = ""
    total_jogadores = 0
    for tipo in ["Gelo Infinito", "Gelo Normal"]:
        if f[tipo]:
            total_jogadores += len(f[tipo])
            mentions = " ".join([f"<@{u.id}>" for u in f[tipo]])
            icon = "♾️" if "Infinito" in tipo else "🧊"
            desc += f"{icon} **{tipo}** ({len(f[tipo])}/{qtd}): {mentions}\n"
    if not desc:
        desc = f"👥 **Jogadores** (0/{qtd})\n`Nenhum jogador na fila.`"
    else:
        desc = f"👥 **Jogadores** ({total_jogadores}/{qtd})\n" + desc
    total, premio, taxa = calcular_premio(valor, qtd)
    emb.description = desc
    emb.add_field(name="💰 Premiação", value=f"Total: {formatar(total)}\nPrêmio: {formatar(premio)}\nTaxa Org: {formatar(taxa)}", inline=False)
    emb.add_field(name="🔑 Pix para pagar", value=f"`{CHAVE_PIX}`", inline=False)
    emb.set_footer(text=f"Taxa: até R$20 = R$0,50/pessoa | acima de R$30 = R$2,50")
    return emb

class FilaView(discord.ui.View):
    def __init__(self, valor, canal_id):
        super().__init__(timeout=None)
        self.valor = valor
        self.canal_id = canal_id

    async def entrar(self, interaction, tipo):
        fila = get_fila(self.canal_id, self.valor)
        for t in fila:
            if interaction.user in fila[t]:
                await interaction.response.send_message(f"❌ Você já está na fila do {t}", ephemeral=True)
                return
        fila[tipo].append(interaction.user)
        canal = bot.get_channel(self.canal_id)
        await interaction.response.defer()
        try:
            await interaction.delete_original_response()
        except: pass
        for msg in [m async for m in canal.history(limit=20)]:
            if msg.author == bot.user and msg.embeds and "Jogadores" in str(msg.embeds[0].description):
                await msg.edit(embed=build_embed_fila(canal, self.valor), view=FilaView(self.valor, self.canal_id))
                break
        qtd = get_qtd_jogadores(canal.name)
        if len(fila[tipo]) >= qtd:
            jogadores = fila[tipo][:qtd]
            fila[tipo] = fila[tipo][qtd:]
            total, premio, taxa = calcular_premio(self.valor, len(jogadores))
            mentions = " ".join([f"<@{u.id}>" for u in jogadores])
            embed = discord.Embed(title=f"🎮 Partida - {canal.name}", color=0x2B2D31, description=f"**Tipo:** {tipo}\n**Valor:** {formatar(self.valor)}\n**Prêmio:** {formatar(premio)}")
            embed.add_field(name="Jogadores", value=mentions)
            await canal.send(content=mentions, embed=embed)
            for msg in [m async for m in canal.history(limit=20)]:
                if msg.author == bot.user and msg.embeds and "Jogadores" in str(msg.embeds[0].description):
                    await msg.edit(embed=build_embed_fila(canal, self.valor), view=FilaView(self.valor, self.canal_id))
                    break

    @discord.ui.button(label="♾️ Gelo Infinito", style=discord.ButtonStyle.primary)
    async def btn_inf(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.entrar(interaction, "Gelo Infinito")

    @discord.ui.button(label="🧊 Gelo Normal", style=discord.ButtonStyle.secondary)
    async def btn_normal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.entrar(interaction, "Gelo Normal")

@bot.event
async def on_ready(): print(f"ON {bot.user}")

@bot.command()
async def fila(ctx, valor: float = None):
    if valor is None:
        for v in VALORES:
            if eh_canal_alvo(ctx.channel.name):
                embed = build_embed_fila(ctx.channel, v)
                await ctx.channel.send(embed=embed, view=FilaView(v, ctx.channel.id))
        return
    embed = build_embed_fila(ctx.channel, valor)
    await ctx.send(embed=embed, view=FilaView(valor, ctx.channel.id))

@bot.command()
async def reset_total(ctx, filtro: str = "x"):
    if not ctx.author.guild_permissions.administrator: return await ctx.send("❌ Sem permissão")
    apagadas = 0
    for canal in ctx.guild.text_channels:
        if filtro.lower() in canal.name.lower() and eh_canal_alvo(canal.name):
            async for msg in canal.history(limit=100):
                if msg.author == bot.user:
                    try: await msg.delete(); apagadas+=1
                    except: pass
            filas.pop(canal.id, None)
    await ctx.send(f"✅ Reset feito - {apagadas} msgs apagadas. Use!fila para recriar.")

bot.run(TOKEN)
