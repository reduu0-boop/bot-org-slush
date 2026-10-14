import discord, os, re, asyncio
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")
PIX_KEY = os.getenv("PIX_KEY") or "PIX_NAO_CONFIGURADO"
VALORES = [0.70, 1.00, 2.00, 3.00, 5.00, 7.00, 10.00, 15.00, 20.00, 30.00, 50.00, 100.00, 200.00]
CATEGORIA_PARTIDAS = "PARTIDAS"
CATEGORIA_TICKETS = "TICKETS"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
filas = {}
aps = {}

def formatar(v): return f"R$ {v:.2f}".replace('.', ',')
def get_taxa(valor): return 2.50 if valor >= 30 else 0.50
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
        if desc == "**Jogadores**\n": desc += "Nenhum jogador na fila."
        emb.description = desc.strip()
    return emb

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

class AceitarAPView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Aceitar AP", style=discord.ButtonStyle.success, emoji="✅", custom_id="aceitar_ap")
    async def aceitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        cid = interaction.channel.id
        dados = aps.get(cid)
        if not dados:
            return await interaction.response.send_message("Erro: partida nao encontrada.", ephemeral=True)
        if interaction.user.id not in [j.id for j in dados["jogadores"]]:
            return await interaction.response.send_message("Voce nao faz parte dessa AP.", ephemeral=True)
        if interaction.user.id in dados["aceitos"]:
            return await interaction.response.send_message("Voce ja aceitou!", ephemeral=True)

        dados["aceitos"].add(interaction.user.id)
        qtd = len(dados["jogadores"])
        aceitos = len(dados["aceitos"])

        emb = interaction.message.embeds[0]
        lista_aceitos = "\n".join([f"✅ <@{uid}>" for uid in dados["aceitos"]])

        emb.description = (
            f"**Valor:** {formatar(dados['valor'])}\n"
            f"**Taxa:** {formatar(dados['taxa'])}\n"
            f"**Total:** **{formatar(dados['total'])}**\n"
            f"**PIX:** `{PIX_KEY}`\n\n"
            f"**Tipo:** {dados['tipo']}\n"
            f"**Jogadores:** {' '.join([f'<@{j.id}>' for j in dados['jogadores']])}\n\n"
            f"**Aceitaram ({aceitos}/{qtd}):**\n{lista_aceitos}\n\n"
        )

        if aceitos >= qtd:
            emb.title = "✅ PARTIDA LIBERADA - CRIEM A SALA"
            emb.color = 0x00FF00
            emb.description += "\n🎮 **Os 2 aceitaram! Podem criar a sala agora!**"
            await interaction.message.edit(embed=emb, view=FecharPartidaView())
            await interaction.response.send_message("Voce aceitou! Partida liberada!", ephemeral=False)
            await interaction.channel.send(f"@everyone Partida liberada! Criem a sala!")
        else:
            emb.description += f"\n⏳ Aguardando {qtd - aceitos} jogador(es)..."
            await interaction.message.edit(embed=emb)
            await interaction.response.send_message(f"Voce aceitou! ({aceitos}/{qtd})", ephemeral=True)

    @discord.ui.button(label="Recusar", style=discord.ButtonStyle.danger, emoji="❌", custom_id="recusar_ap")
    async def recusar(self, interaction: discord.Interaction, button: discord.ui.Button):
        cid = interaction.channel.id
        dados = aps.get(cid)
        if not dados or interaction.user.id not in [j.id for j in dados["jogadores"]]:
            return await interaction.response.send_message("Voce nao faz parte dessa AP.", ephemeral=True)
        await interaction.response.send_message("AP cancelada, fechando...", ephemeral=False)
        aps.pop(cid, None)
        await asyncio.sleep(3)
        try: await interaction.channel.delete()
        except: pass

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
    taxa = get_taxa(valor)
    total = valor + taxa
    nome_canal_priv = f"ap-{str(valor).replace('.','-')}-{tipo_fila.lower().replace(' ','')[:4]}-{jogadores[0].name[:5]}".lower()[:30]
    canal_priv = await guild.create_text_channel(nome_canal_priv, category=categoria, overwrites=overwrites)
    aps[canal_priv.id] = {"jogadores": jogadores, "aceitos": set(), "valor": valor, "taxa": taxa, "total": total, "tipo": tipo_fila}
    emb = discord.Embed(
        title=f"⏳ Aguardando Aceite - {formatar_titulo(canal_origem_nome)}",
        color=0xFFFF00,
        description=(
            f"**Valor:** {formatar(valor)}\n**Taxa:** {formatar(taxa)}\n**Total:** **{formatar(total)}**\n"
            f"**PIX:** `{PIX_KEY}`\n\n**Tipo:** {tipo_fila}\n"
            f"**Jogadores:** {' '.join([f'<@{j.id}>' for j in jogadores])}\n\n"
            f"**Aceitaram (0/{len(jogadores)}):**\nNinguem aceitou ainda\n\n⏳ Aguardando {len(jogadores)} jogador(es) aceitar..."
        )
    )
    mentions = " ".join([f"<@{j.id}>" for j in jogadores])
    await canal_priv.send(content=f"{mentions} - aceitem o AP!", embed=emb, view=AceitarAPView())
    return canal_priv

class FecharPartidaView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Fechar Partida", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="fechar_ap")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        aps.pop(interaction.channel.id, None)
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
        super().__init__(label=label, style=discord.ButtonStyle.secondary, emoji="🎮", custom_id=f"emu_{label}_{cid}_{valor}")
        self.valor=valor; self.cid=cid; self.nome_canal=nome_canal; self.tipo=label
    async def callback(self, interaction: discord.Interaction):
        fila = get_fila(self.cid, self.valor, self.nome_canal)
        for t in fila:
            if interaction.user in fila[t]:
                return await interaction.response.send_message(f"Ja esta no {t}", ephemeral=True)
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
        super().__init__(label=label, style=style, emoji="🧊", custom_id=f"gelo_{label}_{cid}_{valor}")
        self.valor=valor; self.cid=cid; self.nome_canal=nome_canal; self.tipo=label
    async def callback(self, interaction: discord.Interaction):
        fila = get_fila(self.cid, self.valor, self.nome_canal)
        for t in fila:
            if interaction.user in fila[t]:
                return await interaction.response.send_message(f"Ja esta no {t}", ephemeral=True)
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
        super().__init__(label="Sair", style=discord.ButtonStyle.danger, emoji="↩️", custom_id=f"sair_{cid}_{valor}")
        self.valor=valor; self.cid=cid; self.nome_canal=nome_canal
    async def callback(self, interaction: discord.Interaction):
        fila = get_fila(self.cid, self.valor, self.nome_canal)
        saiu=False
        for t in fila:
            if interaction.user in fila[t]:
                fila[t].remove(interaction.user); saiu=True
        if not saiu: return await interaction.response.send_message("Voce nao esta nessa fila", ephemeral=True)
        canal = bot.get_channel(self.cid)
        await interaction.response.defer()
        await achar_e_editar(canal, self.valor, self.nome_canal)

class AbrirTicketButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Abrir Ticket", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="abrir_ticket")
    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        categoria = discord.utils.get(guild.categories, name=CATEGORIA_TICKETS)
        if not categoria:
            categoria = await guild.create_category(CATEGORIA_TICKETS)
        for ch in categoria.text_channels:
            if ch.topic and str(interaction.user.id) in ch.topic:
                return await interaction.response.send_message(f"Voce ja tem um ticket aberto: {ch.mention}", ephemeral=True)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        }
        for role in guild.roles:
            if "staff" in role.name.lower() or "adm" in role.name.lower() or "mod" in role.name.lower() or "suporte" in role.name.lower():
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        canal = await guild.create_text_channel(f"ticket-{interaction.user.name}", category=categoria, topic=str(interaction.user.id), overwrites=overwrites)
        emb = discord.Embed(title="SUPORTE ORG SLUSH", description=f"Ola {interaction.user.mention}, seu ticket foi criado!\n\nDescreva seu problema que um staff vai te atender.", color=0x00FF88)
        await canal.send(content=f"{interaction.user.mention}", embed=emb, view=FecharTicketView())
        await interaction.response.send_message(f"Ticket criado: {canal.mention}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(AbrirTicketButton())

class FecharTicketView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="fechar_ticket")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Fechando em 5s...")
        await asyncio.sleep(5)
        try: await interaction.channel.delete()
        except: pass

@bot.event
async def on_ready():
    print(f"ON {bot.user}")
    bot.add_view(TicketView())
    bot.add_view(FecharTicketView())
    bot.add_view(FecharPartidaView())
    bot.add_view(AceitarAPView())

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
async def suporte(ctx):
    emb = discord.Embed(title="SUPORTE ORG SLUSH", description="Clique abaixo para abrir ticket privado.", color=0x5865F2)
    await ctx.send(embed=emb, view=TicketView())

@bot.command()
async def reset_total(ctx):
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("Voce precisa ser ADM.")
    await ctx.send("🔄 Apagando tudo... aguarde 1 minuto.")
    apag=0
    for canal in ctx.guild.text_channels:
        if eh_canal_alvo(canal.name):
            try:
                async for msg in canal.history(limit=500):
                    if msg.author == bot.user:
                        try:
                            await msg.delete()
                            apag+=1
                            await asyncio.sleep(0.4)
                        except: pass
                filas.pop(canal.id, None)
            except: pass
    await ctx.send(f"✅ Reset finalizado! Apaguei {apag} msgs. Agora use `!fila`")

bot.run(TOKEN)
