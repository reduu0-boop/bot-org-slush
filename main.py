import discord
from discord.ext import commands
import json
import os
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

VALORES = ["1", "2", "3", "5", "10", "15", "20", "30", "40", "50", "75", "100", "150"]
COR = 0x2ECC71
ARQUIVO_FILAS = "filas.json"
ARQUIVO_BLACKLIST = "blacklist.json"
ARQUIVO_SALAS = "salas.json"

def load_json(path, default):
    if not os.path.exists(path): return default
    try:
        with open(path, "r") as f: return json.load(f)
    except: return default

def save_json(path, data):
    with open(path, "w") as f: json.dump(data, f, indent=4)

def get_modo(nome_canal):
    n = nome_canal.lower()
    if "mobile" in n: return "1x1 Mobile"
    if "emulador" in n: return "1x1 Emulador"
    if "misto" in n: return "1x1 Misto"
    if "4x4-mobile" in n: return "4x4 Mobile"
    if "4x4-emulador" in n: return "4x4 Emulador"
    return "1x1 Mobile"

def get_qtd(modo):
    return 8 if "4x4" in modo else 2

def build_desc_mobile(lista, necessario):
    inf = [p for p in lista if p.get("tipo") == "inf"]
    normal = [p for p in lista if p.get("tipo") == "normal"]
    
    def fmt(jogadores):
        if not jogadores: return "Nenhum jogador na fila."
        return "\n".join([f"<@{j['id']}>" for j in jogadores])

    return f"**Jogadores**\n❄️ Gelo Infinito ({len(inf)}/{necessario}):\n{fmt(inf)}\n\n🧊 Gelo Normal ({len(normal)}/{necessario}):\n{fmt(normal)}"

def get_titulo(modo, valor):
    return f"• {modo} • R$ {valor} •"
    async def criar_sala_privada(guild, modo, valor, tipo_gelo, jogadores):
    cat = discord.utils.get(guild.categories, name="PARTIDAS ATIVAS")
    if not cat:
        cat = await guild.create_category("PARTIDAS ATIVAS")

    overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
    for j in jogadores:
        try:
            m = guild.get_member(int(j["id"]))
            if m: overwrites[m] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        except: pass
    overwrites[guild.me] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    tipo_txt = "INFINITO" if tipo_gelo == "inf" else "NORMAL"
    canal = await guild.create_text_channel(
        name=f"🎮・{modo}-R${valor}-{tipo_txt}".lower().replace(" ", "-")[:90],
        category=cat, overwrites=overwrites
    )

    sala_id = str(canal.id)
    salas = load_json(ARQUIVO_SALAS, {})
    salas[sala_id] = {"jogadores": [j["id"] for j in jogadores], "aceitos": [], "modo": modo, "valor": valor, "tipo": tipo_txt}
    save_json(ARQUIVO_SALAS, salas)

    embed = discord.Embed(
        title=f"• {modo} • R$ {valor} • Gelo {tipo_txt} •",
        description=f"Partida fechou!\n\nJogadores:\n" + "\n".join([f"<@{j['id']}>" for j in jogadores]) + "\n\nClique em aceitar para confirmar.",
        color=COR
    )
    await canal.send(f"{' '.join([f'<@{j[\"id\"]}>' for j in jogadores])}", embed=embed, view=ViewSala())
    return canal

class ViewSala(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Aceitar", style=discord.ButtonStyle.success, emoji="✅", custom_id="sala:aceitar")
    async def aceitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        salas = load_json(ARQUIVO_SALAS, {})
        sala = salas.get(str(interaction.channel.id))
        if not sala: return await interaction.response.send_message("Sala não encontrada.", ephemeral=True)
        if str(interaction.user.id) not in sala["jogadores"]:
            return await interaction.response.send_message("Você não está nessa partida.", ephemeral=True)
        if str(interaction.user.id) not in sala["aceitos"]:
            sala["aceitos"].append(str(interaction.user.id))
            save_json(ARQUIVO_SALAS, salas)

        aceitos_txt = ", ".join([f"<@{i}>" for i in sala["aceitos"]]) if sala["aceitos"] else "Ninguém"
        await interaction.response.send_message(f"Você aceitou! Aceitaram: {aceitos_txt}", ephemeral=False)

        if len(sala["aceitos"]) == len(sala["jogadores"]):
            await interaction.channel.send("✅ **Todos aceitaram! Chamem um moderador para iniciar.** @here")
            class ViewMobileEmu(discord.ui.View):
    def __init__(self, modo, valor):
        super().__init__(timeout=None)
        self.modo = modo
        self.valor = valor
        

    @discord.ui.button(label="Recusar", style=discord.ButtonStyle.danger, emoji="❌", custom_id="sala:recusar")
    async def recusar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Partida cancelada. Apagando sala em 5s...", ephemeral=False)
        salas = load_json(ARQUIVO_SALAS, {})
        salas.pop(str(interaction.channel.id), None)
        save_json(ARQUIVO_SALAS, salas)
        await asyncio.sleep(5)
        await interaction.channel.delete(reason="Partida recusada")
        @discord.ui.button(label="Gelo Infinito", style=discord.ButtonStyle.primary, emoji="❄️", custom_id="mob:inf")
    async def btn_inf(self, interaction, button):
                async def entrar_fila(self, interaction, tipo_gelo):
        uid = str(interaction.user.id)
        chave = f"{self.modo}_{self.valor}_{tipo_gelo}"

        filas = load_json(ARQUIVO_FILAS, {})
        if chave not in filas: filas[chave] = []

        # verifica se ja esta em alguma fila
        for k, lista in filas.items():
            if any(j["id"] == uid for j in lista):
                return await interaction.response.send_message(f"Você já está na fila {k}", ephemeral=True)

        filas[chave].append({"id": uid, "nome": interaction.user.display_name})
        save_json(ARQUIVO_FILAS, filas)

        await interaction.response.send_message(f"✅ Entrou na fila {self.modo} R${self.valor} - Gelo {tipo_gelo}", ephemeral=True)

        qtd = len(filas[chave])
        limite = 4 if self.modo == "4x4" else 6 if self.modo == "6x6" else 4
        await interaction.followup.send(f"👥 {qtd}/{limite} jogadores na fila.", ephemeral=True)

        if qtd >= limite:
            jogadores = filas[chave][:limite]
            filas[chave] = filas[chave][limite:]
            save_json(ARQUIVO_FILAS, filas)
            canal = await criar_sala_privada(interaction.guild, self.modo, self.valor, tipo_gelo, jogadores)
            await interaction.followup.send(f"🎮 Partida fechada! Vá para {canal.mention}", ephemeral=True)

    async def sair_fila(self, interaction):
        uid = str(interaction.user.id)
        filas = load_json(ARQUIVO_FILAS, {})
        achou = False
        for k in list(filas.keys()):
            antes = len(filas[k])
            filas[k] = [j for j in filas[k] if j["id"]!= uid]
            if len(filas[k])!= antes: achou = True
        save_json(ARQUIVO_FILAS, filas)
        if achou:
            await interaction.response.send_message("🚪 Saiu de todas as filas.", ephemeral=True)
        else:
            await interaction.response.send_message("Você não está em fila.", ephemeral=True)
        await self.entrar_fila(interaction, "inf")

    @discord.ui.button(label="Gelo Normal", style=discord.ButtonStyle.secondary, emoji="🧊", custom_id="mob:normal")
    async def btn_normal(self, interaction, button):
        await self.entrar_fila(interaction, "normal")

    @discord.ui.button(label="Sair da Fila", style=discord.ButtonStyle.danger, emoji="🚪", custom_id="mob:sair")
    async def btn_sair(self, interaction, button):
        await self.sair_fila(interaction)
    @bot.event
async def on_ready():
    print(f"Logado como {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Sync {len(synced)} comandos")
    except Exception as e:
        print(e)

@bot.tree.command(name="painel_apostas", description="Criar painel de apostas")
@discord.app_commands.checks.has_permissions(administrator=True)
async def painel_apostas(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎮 CRIAR SALA APOSTADA 🎮",
        description="Escolha o modo, valor e tipo de gelo abaixo.\n\n**Modos:** 4x4 Emulador / 6x6 Mobile\n**Valores:** 5, 10, 20, 50, etc\n**Gelo:** Infinito ou Normal",
        color=COR
    )
    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="4x4 - R$5", style=discord.ButtonStyle.success, custom_id="criar:4x4_5"))
    view.add_item(discord.ui.Button(label="4x4 - R$10", style=discord.ButtonStyle.success, custom_id="criar:4x4_10"))
    view.add_item(discord.ui.Button(label="6x6 - R$5", style=discord.ButtonStyle.primary, custom_id="criar:6x6_5"))
    view.add_item(discord.ui.Button(label="6x6 - R$10", style=discord.ButtonStyle.primary, custom_id="criar:6x6_10"))
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="limpar_filas", description="Limpar todas as filas")
@discord.app_commands.checks.has_permissions(administrator=True)
async def limpar_filas(interaction: discord.Interaction):
    save_json(ARQUIVO_FILAS, {})
    await interaction.response.send_message("✅ Filas limpas!", ephemeral=True)
    @bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return
    cid = interaction.data.get("custom_id","")
    if not cid.startswith("criar:"):
        return

    try:
        _, dados = cid.split(":",1)
        modo, valor = dados.split("_")
    except:
        return

    embed = discord.Embed(
        title=f"• {modo} • R$ {valor} •",
        description=f"**Fila aberta para {modo} valendo R$ {valor}**\n\nEscolha o tipo de gelo:\n❄️ Infinito\n🧊 Normal\n\nClique abaixo para entrar!",
        color=COR
    )
    await interaction.response.send_message(embed=embed, view=ViewMobileEmu(modo, valor))

# RODA
bot.run(TOKEN)
