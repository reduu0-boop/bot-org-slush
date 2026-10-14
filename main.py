import discord
from discord.ext import commands
import json, os, datetime, asyncio

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

BLACKLIST_FILE = "blacklist.json"
AP_FILE = "ap_data.json"
FILA_FILE = "filas.json"

def load_bl():
    if not os.path.exists(BLACKLIST_FILE): return {}
    try:
        with open(BLACKLIST_FILE, "r") as f: return json.load(f)
    except: return {}
def save_bl(data):
    with open(BLACKLIST_FILE, "w") as f: json.dump(data, f, indent=4)

def load_ap():
    if not os.path.exists(AP_FILE): return {}
    try:
        with open(AP_FILE, "r") as f: return json.load(f)
    except: return {}
def save_ap(data):
    with open(AP_FILE, "w") as f: json.dump(data, f, indent=4)

def load_filas():
    if not os.path.exists(FILA_FILE): return {}
    try:
        with open(FILA_FILE, "r") as f: return json.load(f)
    except: return {}
def save_filas(data):
    with open(FILA_FILE, "w") as f: json.dump(data, f, indent=4)

def qtd_necessaria(nome_canal):
    nome = nome_canal.lower()
    if "1x1" in nome: return 2
    if "2x2" in nome: return 4
    if "3x3" in nome: return 6
    if "4x4" in nome: return 8
    return 2

# ===== BLACKLIST =====
class ConsultarIDModal(discord.ui.Modal, title="Consultar ID na Blacklist"):
    id_input = discord.ui.TextInput(label="Digite o ID", placeholder="Ex: 123456789")
    async def on_submit(self, interaction: discord.Interaction):
        data = load_bl()
        id_p = self.id_input.value.strip()
        if id_p in data:
            info = data[id_p]
            embed = discord.Embed(title="⛔ ESTÁ NA BLACKLIST", color=0xff0000)
            embed.add_field(name="ID", value=id_p)
            embed.add_field(name="Nick", value=info.get('nick','-'))
            embed.add_field(name="Motivo", value=info['motivo'], inline=False)
            embed.add_field(name="Data", value=info['data'])
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=discord.Embed(title="✅ LIMPO", description=f"ID `{id_p}` não está na blacklist.", color=0x00ff00), ephemeral=True)

class ConsultarNickModal(discord.ui.Modal, title="Consultar Jogador"):
    nick_input = discord.ui.TextInput(label="Digite o nick")
    async def on_submit(self, interaction: discord.Interaction):
        data = load_bl()
        busca = self.nick_input.value.lower()
        achados = [(k,v) for k,v in data.items() if busca in v.get('nick','').lower()]
        if achados:
            desc = "\n".join([f"**{v.get('nick')}** - ID: {k} | {v['motivo']}" for k,v in achados[:10]])
            await interaction.response.send_message(embed=discord.Embed(title=f"⛔ {len(achados)} encontrados", description=desc, color=0xff0000), ephemeral=True)
        else:
            await interaction.response.send_message(embed=discord.Embed(title="✅ NADA ENCONTRADO", description="Nenhum nick parecido.", color=0x00ff00), ephemeral=True)

class BlacklistView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Consultar ID", style=discord.ButtonStyle.secondary, emoji="🔍", custom_id="bl_id")
    async def b1(self, interaction, button): await interaction.response.send_modal(ConsultarIDModal())
    @discord.ui.button(label="Consultar Jogador", style=discord.ButtonStyle.secondary, emoji="🔍", custom_id="bl_nick")
    async def b2(self, interaction, button): await interaction.response.send_modal(ConsultarNickModal())

# ===== FILA VIEW =====
class FilaView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="Gelo Infinito", style=discord.ButtonStyle.primary, emoji="❄️", custom_id="fila_gelo_inf")
    async def gelo_inf(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.entrar_fila(interaction, "Gelo Infinito")

    @discord.ui.button(label="Gelo Normal", style=discord.ButtonStyle.secondary, emoji="🧊", custom_id="fila_gelo_normal")
    async def gelo_normal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.entrar_fila(interaction, "Gelo Normal")

    @discord.ui.button(label="Sair", style=discord.ButtonStyle.danger, emoji="🚪", custom_id="fila_sair")
    async def sair(self, interaction: discord.Interaction, button: discord.ui.Button):
        filas = load_filas()
        canal_id = str(interaction.channel.id)
        lista = filas.get(canal_id, [])
        if str(interaction.user.id) in lista:
            lista.remove(str(interaction.user.id))
            filas[canal_id] = lista
            save_filas(filas)
            await interaction.response.send_message("Você saiu da fila.", ephemeral=True)
            await self.atualizar_embed(interaction.channel)
        else:
            await interaction.response.send_message("Você nem está na fila.", ephemeral=True)

    async def entrar_fila(self, interaction: discord.Interaction, tipo):
        bl = load_bl()
        if str(interaction.user.id) in bl:
            await interaction.response.send_message(f"⛔ Você está na blacklist!", ephemeral=True)
            return
        filas = load_filas()
        canal_id = str(interaction.channel.id)
        lista = filas.get(canal_id, [])
        if str(interaction.user.id) in lista:
            await interaction.response.send_message("Você já está na fila!", ephemeral=True)
            return
        lista.append(str(interaction.user.id))
        filas[canal_id] = lista
        save_filas(filas)
        await interaction.response.send_message(f"✅ Entrou na fila [{tipo}]!", ephemeral=True)
        await self.atualizar_embed(interaction.channel)
        necessario = qtd_necessaria(interaction.channel.name)
        if len(lista) >= necessario:
            mencoes = " ".join([f"<@{uid}>" for uid in lista[:necessario]])
            await interaction.channel.send(f"🔥 **FILA FECHOU!** {mencoes}\nModo: {tipo} - {interaction.channel.name}")
            filas[canal_id] = lista[necessario:]
            save_filas(filas)
            await self.atualizar_embed(interaction.channel)

    async def atualizar_embed(self, canal):
        filas = load_filas()
        lista = filas.get(str(canal.id), [])
        necessario = qtd_necessaria(canal.name)
        embed = discord.Embed(
            title=f"🎮 FILA - {canal.name.upper()}",
            description=f"**Jogadores na fila: {len(lista)}/{necessario}**\n\n" + ("\n".join([f"{i+1}. <@{uid}>" for i, uid in enumerate(lista)]) if lista else "*Fila vazia - clique para entrar*"),
            color=0x2b2d31
        )
        try:
            async for msg in canal.history(limit=20):
                if msg.author == canal.guild.me and msg.embeds and "FILA -" in msg.embeds[0].title:
                    await msg.edit(embed=embed, view=FilaView())
                    return
        except: pass

# ===== AP VIEW =====
class AprovacaoView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Aceitar AP", style=discord.ButtonStyle.success, custom_id="aceitar_ap")
    async def aceitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        aps = load_ap()
        canal_id = str(interaction.channel.id)
        if canal_id not in aps:
            await interaction.response.send_message("Sala não encontrada.", ephemeral=True); return
        ticket = aps[canal_id]
        user_id = str(interaction.user.id)
        if user_id not in ticket["aceitaram"]:
            ticket["aceitaram"].append(user_id)
            save_ap(aps)
        if len(ticket["aceitaram"]) >= 2:
            await interaction.channel.send(embed=discord.Embed(title="✅ AP CONFIRMADO", description=f"AP de R$ {ticket['valor']} confirmado!", color=0x00ff00))
            await interaction.response.send_message("Você aceitou!", ephemeral=True)
        else:
            await interaction.response.send_message("Você aceitou! Aguardando o outro.", ephemeral=True)
    @discord.ui.button(label="Cancelar AP", style=discord.ButtonStyle.danger, custom_id="cancelar_ap")
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.send(f"❌ AP cancelado por {interaction.user.mention}")

@bot.event
async def on_ready():
    print(f"Online: {bot.user}")
    bot.add_view(BlacklistView())
    bot.add_view(FilaView())
    bot.add_view(AprovacaoView())
    try: await bot.tree.sync()
    except: pass

async def limpar_e_criar_fila(canal):
    try:
        await canal.purge(limit=100)
        await asyncio.sleep(0.5)
        await canal.purge(limit=100)
        necessario = qtd_necessaria(canal.name)
        embed = discord.Embed(
            title=f"🎮 FILA - {canal.name.upper()}",
            description=f"**Jogadores na fila: 0/{necessario}**\n\n*Fila vazia - clique para entrar*\n\n❄️ Gelo Infinito | 🧊 Gelo Normal",
            color=0x2b2d31
        )
        await canal.send(embed=embed, view=FilaView())
        return True
    except Exception as e:
        print(f"Erro no canal {canal.name}: {e}")
        return False

@bot.tree.command(name="blacklist_setup", description="Cria o painel da blacklist")
async def blacklist_setup(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Só ADM", ephemeral=True); return
    embed = discord.Embed(title="Blacklist", description="Clique no botão abaixo para verificar um ID na blacklist.", color=0x2b2d31)
    await interaction.channel.send(embed=embed, view=BlacklistView())
    await interaction.response.send_message("Painel criado!", ephemeral=True)

@bot.tree.command(name="bl_add", description="Add na blacklist")
async def bl_add(interaction: discord.Interaction, id_jogador: str, nick: str, motivo: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Só ADM", ephemeral=True); return
    data = load_bl()
    data[id_jogador] = {"nick": nick, "motivo": motivo, "data": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), "por": str(interaction.user)}
    save_bl(data)
    await interaction.response.send_message(f"⛔ {nick} ({id_jogador}) adicionado.", ephemeral=True)

@bot.tree.command(name="bl_remove", description="Remove da blacklist")
async def bl_remove(interaction: discord.Interaction, id_jogador: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Só ADM", ephemeral=True); return
    data = load_bl()
    if id_jogador in data:
        del data[id_jogador]; save_bl(data)
        await interaction.response.send_message(f"ID {id_jogador} removido.", ephemeral=True)
    else:
        await interaction.response.send_message("ID não está na blacklist.", ephemeral=True)

@bot.tree.command(name="ap", description="Criar sala de AP 1x1")
async def ap(interaction: discord.Interaction, adversario: discord.Member, valor: str, id_adversario: str = None):
    if id_adversario:
        bl = load_bl()
        if id_adversario in bl:
            await interaction.response.send_message(f"⛔ NEGADO! ID na blacklist.", ephemeral=True)
            return
    guild = interaction.guild
    categoria = discord.utils.get(guild.categories, name="AP - ATIVO")
    if not categoria:
        categoria = await guild.create_category("AP - ATIVO")
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        adversario: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
    }
    canal = await guild.create_text_channel(f"ap-{interaction.user.name}-{adversario.name}", category=categoria, overwrites=overwrites)
    aps = load_ap()
    aps[str(canal.id)] = {"valor": valor, "jogadores": [str(interaction.user.id), str(adversario.id)], "aceitaram": []}
    save_ap(aps)
    embed = discord.Embed(title="💰 SALA DE AP CRIADA", description=f"{interaction.user.mention} vs {adversario.mention}\n**Valor: R$ {valor}**", color=0x2b2d31)
    await canal.send(content=f"{interaction.user.mention} {adversario.mention}", embed=embed, view=AprovacaoView())
    await interaction.response.send_message(f"Sala criada: {canal.mention}", ephemeral=True)

@bot.command(name="reset_total")
@commands.has_permissions(administrator=True)
async def reset_total(ctx):
    await ctx.send("🔄 Limpando todas as filas... Aguarde.")
    save_filas({})
    alvos = ["1x1-mobile", "2x2-mobile", "3x3-mobile", "4x4-mobile", "1x1-emulador", "2x2-emulador", "3x3-emulador", "4x4-emulador", "2x2-misto", "3x3-misto", "4x4-misto", "1x1-misto"]
    count = 0
    canais_para_limpar = []
    for canal in ctx.guild.text_channels:
        for alvo in alvos:
            if alvo in canal.name.lower():
                canais_para_limpar.append(canal)
                break
    for canal in canais_para_limpar:
        ok = await limpar_e_criar_fila(canal)
        if ok: count += 1
        await asyncio.sleep(1)
    await ctx.send(f"✅ **{count} fileiras recriadas!**\nBlacklist continua ativa.")

bot.run(os.getenv("DISCORD_TOKEN"))
