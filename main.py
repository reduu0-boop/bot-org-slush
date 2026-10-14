import discord
from discord.ext import commands
import json, os, datetime

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

BLACKLIST_FILE = "blacklist.json"
TICKET_FILE = "tickets.json"

# ===== FUNÇÕES BLACKLIST =====
def load_bl():
    if not os.path.exists(BLACKLIST_FILE): return {}
    with open(BLACKLIST_FILE, "r") as f: return json.load(f)
def save_bl(data):
    with open(BLACKLIST_FILE, "w") as f: json.dump(data, f, indent=4)

def load_tickets():
    if not os.path.exists(TICKET_FILE): return {}
    with open(TICKET_FILE, "r") as f: return json.load(f)
def save_tickets(data):
    with open(TICKET_FILE, "w") as f: json.dump(data, f, indent=4)

# ===== MODAIS BLACKLIST - IGUAL DA FOTO =====
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
    nick_input = discord.ui.TextInput(label="Digite o nick", placeholder="Ex: Cauan_ff")
    async def on_submit(self, interaction: discord.Interaction):
        data = load_bl()
        busca = self.nick_input.value.lower()
        achados = [(k,v) for k,v in data.items() if busca in v.get('nick','').lower()]
        if achados:
            desc = "\n".join([f"**{v.get('nick')}** - ID: {k} | {v['motivo']}" for k,v in achados[:10]])
            await interaction.response.send_message(embed=discord.Embed(title=f"⛔ {len(achados)} encontrados", description=desc, color=0xff0000), ephemeral=True)
        else:
            await interaction.response.send_message(embed=discord.Embed(title="✅ NADA ENCONTRADO", description="Nenhum nick parecido na blacklist.", color=0x00ff00), ephemeral=True)

class BlacklistView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Consultar ID", style=discord.ButtonStyle.secondary, emoji="🔍", custom_id="bl_id")
    async def b1(self, interaction, button): await interaction.response.send_modal(ConsultarIDModal())
    @discord.ui.button(label="Consultar Jogador", style=discord.ButtonStyle.secondary, emoji="🔍", custom_id="bl_nick")
    async def b2(self, interaction, button): await interaction.response.send_modal(ConsultarNickModal())

# ===== SISTEMA DE AP (1x1) =====
class AprovacaoView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Aceitar AP", style=discord.ButtonStyle.success, custom_id="aceitar_ap")
    async def aceitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        tickets = load_tickets()
        canal_id = str(interaction.channel.id)
        if canal_id not in tickets:
            await interaction.response.send_message("Ticket não encontrado.", ephemeral=True); return
        
        ticket = tickets[canal_id]
        user_id = str(interaction.user.id)

        if user_id not in ticket["aceitaram"]:
            ticket["aceitaram"].append(user_id)
            save_tickets(tickets)

        if len(ticket["aceitaram"]) >= 2:
            embed = discord.Embed(title="✅ AP CONFIRMADO", description=f"Os dois confirmaram!\nAP de R$ {ticket['valor']}\nPode começar.", color=0x00ff00)
            await interaction.channel.send(embed=embed)
            await interaction.response.send_message("Você aceitou!", ephemeral=True)
        else:
            await interaction.response.send_message("Você aceitou! Aguardando o outro jogador aceitar.", ephemeral=True)

    @discord.ui.button(label="Cancelar AP", style=discord.ButtonStyle.danger, custom_id="cancelar_ap")
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.send(f"❌ AP cancelado por {interaction.user.mention}")
        await interaction.response.send_message("AP cancelado.", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Online: {bot.user}")
    bot.add_view(BlacklistView())
    bot.add_view(AprovacaoView())
    try: await bot.tree.sync()
    except: pass

# ===== COMANDOS =====
@bot.tree.command(name="blacklist_setup", description="Cria o painel da blacklist igual da foto")
async def blacklist_setup(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Só ADM", ephemeral=True); return
    embed = discord.Embed(title="Blacklist", description="Clique no botão abaixo para verificar um ID na blacklist.", color=0x2b2d31)
    await interaction.channel.send(embed=embed, view=BlacklistView())
    await interaction.response.send_message("Painel criado igual da foto!", ephemeral=True)

@bot.tree.command(name="bl_add", description="Add na blacklist")
async def bl_add(interaction: discord.Interaction, id_jogador: str, nick: str, motivo: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Só ADM", ephemeral=True); return
    data = load_bl()
    data[id_jogador] = {"nick": nick, "motivo": motivo, "data": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), "por": str(interaction.user)}
    save_bl(data)
    await interaction.response.send_message(f"⛔ {nick} ({id_jogador}) adicionado: {motivo}", ephemeral=True)

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

# COMANDO AP QUE VOCÊ JÁ USA
@bot.tree.command(name="ap", description="Criar sala de AP 1x1")
async def ap(interaction: discord.Interaction, adversario: discord.Member, valor: str, id_adversario: str = None):
    # VERIFICA BLACKLIST AUTOMATICO
    if id_adversario:
        bl = load_bl()
        if id_adversario in bl:
            info = bl[id_adversario]
            await interaction.response.send_message(f"⛔ NEGADO! O ID {id_adversario} está na blacklist.\nMotivo: {info['motivo']}", ephemeral=True)
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
    
    tickets = load_tickets()
    tickets[str(canal.id)] = {"valor": valor, "jogadores": [str(interaction.user.id), str(adversario.id)], "aceitaram": []}
    save_tickets(tickets)

    embed = discord.Embed(title="💰 SALA DE AP CRIADA", description=f"{interaction.user.mention} vs {adversario.mention}\n**Valor: R$ {valor}**\n\nFaçam o PIX e cliquem em Aceitar AP.", color=0x2b2d31)
    await canal.send(content=f"{interaction.user.mention} {adversario.mention}", embed=embed, view=AprovacaoView())
    await interaction.response.send_message(f"Sala criada: {canal.mention}", ephemeral=True)

bot.run(os.getenv("DISCORD_TOKEN"))
