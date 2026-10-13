import discord, os, asyncio, re, requests, uuid
from discord.ext import commands
from datetime import datetime, timedelta

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")
INTER_CLIENT_ID = os.getenv("INTER_CLIENT_ID")
INTER_CLIENT_SECRET = os.getenv("INTER_CLIENT_SECRET")
INTER_CHAVE_PIX = "c2d13650-0370-42e3-a918-0cc68c457646"
CERT = ('certs/certificado.crt', 'certs/chave_privada.key')

TAXA_POR_PESSOA = 0.50
VALORES = [0.70, 1.00, 2.00, 3.00, 5.00, 10.00, 20.00, 30.00, 50.00, 100.00, 200.00]

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

filas = {}
pagamentos_pendentes = {}

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
    # TAXA FIXA CORRIGIDA
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

def get_token_inter():
    url = "https://cdpj.partners.bancointer.com.br/oauth/v2/token"
    data = {'client_id': INTER_CLIENT_ID, 'client_secret': INTER_CLIENT_SECRET, 'scope': 'cob.write cob.read pix.read', 'grant_type': 'client_credentials'}
    r = requests.post(url, data=data, cert=CERT, timeout=20)
    r.raise_for_status()
    return r.json()['access_token']

def gerar_pix_inter(valor, nome="Jogador"):
    token = get_token_inter()
    txid = uuid.uuid4().hex[:26]
    url = f"https://cdpj.partners.bancointer.com.br/pix/v2/cob/{txid}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"calendario": {"expiracao": 600}, "devedor": {"nome": nome[:30]}, "valor": {"original": f"{valor:.2f}"}, "chave": INTER_CHAVE_PIX, "solicitacaoPagador": f"AP {formatar(valor)}"}
    r = requests.put(url, json=payload, headers=headers, cert=CERT, timeout=20)
    if r.status_code not in [200, 201]: raise Exception(f"Erro Inter: {r.text}")
    data = r.json()
    return {"txid": txid, "copia_cola": data.get('pixCopiaECola')}

def checar_pagamento(txid):
    try:
        token = get_token_inter()
        url = f"https://cdpj.partners.bancointer.com.br/pix/v2/cob/{txid}"
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get(url, headers=headers, cert=CERT, timeout=20)
        return r.json().get('status') == 'CONCLUIDA'
    except: return False

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
    emb.set_footer(text=f"Taxa: R$0,50/pessoa até R$20 | R$2,50 acima de R$30")
    return emb

class FilaView(discord.ui.View):
    def __init__(self, valor, canal_id):
        super().__init__(timeout=None)
        self.valor = valor
        self.canal_id = canal_id
    async def entrar_fila(self, interaction, tipo):
        await interaction.response.defer(ephemeral=True)
        fila = get_fila(self.canal_id, self.valor)
        for t in fila:
            if interaction.user in fila[t]:
                await interaction.followup.send(f"❌ Você já está na fila do {t}", ephemeral=True)
                return
        try:
            pix = gerar_pix_inter(self.valor, interaction.user.display_name)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)
            return
        pagamentos_pendentes[pix['txid']] = {"user_id": interaction.user.id, "valor": self.valor, "canal_id": self.canal_id, "tipo": tipo, "expira": datetime.now() + timedelta(seconds=600)}
        embed_pix = discord.Embed(title="💳 Pague para entrar", color=0x00FF88, description=f"**Valor:** {formatar(self.valor)}\n**Pix Copia e Cola:**\n```{pix['copia_cola']}```")
        try:
            await interaction.user.send(embed=embed_pix)
            await interaction.followup.send(f"✅ Pix gerado! Enviei no privado.", ephemeral=True)
        except:
            await interaction.followup.send(embed=embed_pix, ephemeral=True)
        bot.loop.create_task(self.aguardar_pagamento(pix['txid'], interaction.user))
    async def aguardar_pagamento(self, txid, user):
        for _ in range(60):
            await asyncio.sleep(5)
            if txid not in pagamentos_pendentes: return
            if checar_pagamento(txid):
                info = pagamentos_pendentes.pop(txid)
                fila = get_fila(info['canal_id'], info['valor'])
                canal = bot.get_channel(info['canal_id'])
                if not canal: return
                fila[info['tipo']].append(user)
                for msg in [m async for m in canal.history(limit=20)]:
                    if msg.author == bot.user and msg.embeds and "Jogadores" in str(msg.embeds[0].description):
                        await msg.edit(embed=build_embed_fila(canal, info['valor']), view=FilaView(info['valor'], info['canal_id']))
                        break
                qtd = get_qtd_jogadores(canal.name)
                if len(fila[info['tipo']]) >= qtd:
                    await criar_partida(canal, info['valor'], info['tipo'])
                return
        pagamentos_pendentes.pop(txid, None)
    @discord.ui.button(label="♾️ Gelo Infinito", style=discord.ButtonStyle.primary)
    async def btn_infinito(self, interaction: discord.ui.Interaction, button: discord.ui.Button):
        await self.entrar_fila(interaction, "Gelo Infinito")
    @discord.ui.button(label="🧊 Gelo Normal", style=discord.ButtonStyle.secondary)
    async def btn_normal(self, interaction: discord.ui.Interaction, button: discord.ui.Button):
        await self.entrar_fila(interaction, "Gelo Normal")

async def criar_partida(channel, valor, tipo):
    fila = get_fila(channel.id, valor)
    jogadores = fila[tipo][:get_qtd_jogadores(channel.name)]
    fila[tipo] = fila[tipo][get_qtd_jogadores(channel.name):]
    total, premio, taxa = calcular_premio(valor, len(jogadores))
    embed = discord.Embed(title=f"🎮 Partida - {channel.name}", color=0x2B2D31, description=f"**Tipo:** {tipo}\n**Prêmio:** {formatar(premio)}")
    mentions = " ".join([f"<@{u.id}>" for u in jogadores])
    embed.add_field(name="Jogadores", value=mentions)
    await channel.send(content=mentions, embed=embed)
    for msg in [m async for m in channel.history(limit=20)]:
        if msg.author == bot.user and msg.embeds and "Jogadores" in str(msg.embeds[0].description):
            await msg.edit(embed=build_embed_fila(channel, valor), view=FilaView(valor, channel.id))
            break

@bot.event
async def on_ready(): print(f"LOGADO {bot.user}")

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
                    try: await msg.delete(); apagadas += 1
                    except: pass
            filas.pop(canal.id, None)
    await ctx.send(f"✅ Reset {apagadas} msgs.")

bot.run(TOKEN)
