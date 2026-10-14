import discord
from discord.ext import commands
import json, os, asyncio, datetime

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

FILA_FILE = "filas.json"
BLACKLIST_FILE = "blacklist.json"

VALORES = ["0,70", "1,00", "2,00", "3,00", "4,00", "5,00", "10,00", "15,00", "20,00", "30,00", "50,00", "100,00", "200,00"]

def load_bl():
    if not os.path.exists(BLACKLIST_FILE): return {}
    try:
        with open(BLACKLIST_FILE,"r") as f: return json.load(f)
    except: return {}
def load_filas():
    if not os.path.exists(FILA_FILE): return {}
    try:
        with open(FILA_FILE,"r") as f: return json.load(f)
    except: return {}
def save_filas(d):
    with open(FILA_FILE,"w") as f: json.dump(d,f,indent=4)

def qtd_necessaria(nome):
    n=nome.lower()
    if "1x1" in n: return 2
    if "2x2" in n: return 4
    if "3x3" in n: return 6
    if "4x4" in n: return 8
    return 2

def get_titulo_modo(nome_canal):
    n = nome_canal.lower()
    if "1x1-mobile" in n: return "1v1 Mobile"
    if "2x2-mobile" in n: return "2v2 Mobile"
    if "3x3-mobile" in n: return "3v3 Mobile"
    if "4x4-mobile" in n: return "4v4 Mobile"
    if "1x1-emulador" in n: return "1v1 Emulador"
    if "2x2-emulador" in n: return "2v2 Emulador"
    if "3x3-emulador" in n: return "3v3 Emulador"
    if "4x4-emulador" in n: return "4v4 Emulador"
    if "2x2-misto" in n: return "2v2 Misto"
    if "3x3-misto" in n: return "3v3 Misto"
    if "4x4-misto" in n: return "4v4 Misto"
    return nome_canal

# ===== VIEWS =====
class ViewMobileEmu(discord.ui.View):
    def __init__(self, modo, valor):
        super().__init__(timeout=None)
        self.modo = modo
        self.valor = valor
        self.add_item(discord.ui.Button(label="Gelo Infinito", style=discord.ButtonStyle.primary, emoji="🧊", custom_id=f"gelo:{modo}:{valor}:inf"))
        self.add_item(discord.ui.Button(label="Gelo Normal", style=discord.ButtonStyle.secondary, emoji="🧊", custom_id=f"gelo:{modo}:{valor}:normal"))
        self.add_item(discord.ui.Button(label="Sair", style=discord.ButtonStyle.danger, emoji="↩️", custom_id=f"gelo:{modo}:{valor}:sair"))

class ViewMisto(discord.ui.View):
    def __init__(self, modo, valor, max_emu):
        super().__init__(timeout=None)
        self.modo = modo
        self.valor = valor
        for i in range(1, max_emu+1):
            self.add_item(discord.ui.Button(label=f"{i} Emu", style=discord.ButtonStyle.secondary, custom_id=f"misto:{modo}:{valor}:{i}emu"))
        self.add_item(discord.ui.Button(label="Sair", style=discord.ButtonStyle.danger, emoji="📤", custom_id=f"misto:{modo}:{valor}:sair"))

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type!= discord.InteractionType.component:
        return
    custom_id = interaction.data.get("custom_id","")
    if not (custom_id.startswith("gelo:") or custom_id.startswith("misto:")):
        return

    if str(interaction.user.id) in load_bl():
        await interaction.response.send_message("⛔ Você está na blacklist", ephemeral=True)
        return

    try:
        tipo, modo, valor, acao = custom_id.split(":")
    except:
        return

    filas = load_filas()
    key = f"{interaction.channel.id}_{valor}"
    lista = filas.get(key, [])

    # SAIR
    if acao == "sair":
        lista = [x for x in lista if x["id"]!= str(interaction.user.id)]
        filas[key] = lista
        save_filas(filas)
        await interaction.response.send_message(f"Saiu da fila R$ {valor}", ephemeral=True)
    else:
        # Já está?
        if any(x["id"] == str(interaction.user.id) for x in lista):
            await interaction.response.send_message("Você já está nessa fila! Clique em Sair para trocar.", ephemeral=True)
            return

        if tipo == "gelo":
            gelo_tipo = "Gelo Infinito" if acao == "inf" else "Gelo Normal"
            lista.append({"id": str(interaction.user.id), "info": gelo_tipo})
        else: # misto
            lista.append({"id": str(interaction.user.id), "info": f"{acao.replace('emu','')} Emu"})

        filas[key] = lista
        save_filas(filas)
        await interaction.response.send_message(f"✅ Entrou: {modo} R$ {valor}", ephemeral=True)

    # ATUALIZA EMBED - IGUAL DA SUA PRINT
    try:
        if not lista:
            desc_jogadores = "Nenhum jogador na fila."
        else:
            linhas = []
            for p in lista:
                # Mostra o nome embaixo de Jogadores
                linhas.append(f"<@{p['id']}>")
            desc_jogadores = "\n".join(linhas)

        embed = discord.Embed(
            title=f"• {modo} • R$ {valor}",
            description=f"**Jogadores**\n{desc_jogadores}",
            color=0x2ECC71 # VERDE igual você pediu
        )

        # Recria a view correta
        if tipo == "gelo":
            view = ViewMobileEmu(modo, valor)
        else:
            max_emu = 1 if "2v2" in modo else 2 if "3v3" in modo else 3
            view = ViewMisto(modo, valor, max_emu)

        await interaction.message.edit(embed=embed, view=view)

        # Fecha fila se lotou
        nec = qtd_necessaria(interaction.channel.name)
        if len(lista) >= nec:
            mencoes = " ".join([f"<@{p['id']}>" for p in lista[:nec]])
            await interaction.channel.send(f"🔥 **FILA FECHOU • {modo} • R$ {valor}** - {mencoes}")
            filas[key] = lista[nec:]
            save_filas(filas)
            embed2 = discord.Embed(title=f"• {modo} • R$ {valor}", description="**Jogadores**\nNenhum jogador na fila.", color=0x2ECC71)
            await interaction.message.edit(embed=embed2, view=view)

    except Exception as e:
        print(f"Erro update: {e}")

@bot.event
async def on_ready():
    print(f"Online {bot.user}")
    # Registra views persistentes
    for modo in ["1v1 Mobile","2v2 Mobile","3v3 Mobile","4v4 Mobile","1v1 Emulador","2v2 Emulador","3v3 Emulador","4v4 Emulador"]:
        for v in VALORES:
            bot.add_view(ViewMobileEmu(modo, v))
    for modo in ["2v2 Misto","3v3 Misto","4v4 Misto"]:
        max_emu = 1 if "2v2" in modo else 2 if "3v3" in modo else 3
        for v in VALORES:
            bot.add_view(ViewMisto(modo, v, max_emu))
    try: await bot.tree.sync()
    except: pass

async def limpar_e_criar_fila(canal):
    try:
        await canal.purge(limit=100)
        await asyncio.sleep(0.5)
        await canal.purge(limit=100)

        modo = get_titulo_modo(canal.name)
        is_misto = "misto" in canal.name.lower()

        # Cria as 13 mensagens do maior para o menor (200,00 no topo igual da print)
        for valor in reversed(VALORES):
            embed = discord.Embed(
                title=f"• {modo} • R$ {valor}",
                description="**Jogadores**\nNenhum jogador na fila.",
                color=0x2ECC71 # VERDE
            )
            if is_misto:
                max_emu = 1 if "2x2" in canal.name.lower() else 2 if "3x3" in canal.name.lower() else 3
                view = ViewMisto(modo, valor, max_emu)
            else:
                view = ViewMobileEmu(modo, valor)

            await canal.send(embed=embed, view=view)
            await asyncio.sleep(0.35)
        return True
    except Exception as e:
        print(f"Erro {canal.name}: {e}")
        return False

@bot.command(name="reset_total")
@commands.has_permissions(administrator=True)
async def reset_total(ctx):
    await ctx.send(f"🔄 Limpando e criando 13 fileiras por canal com modelo da print...")
    save_filas({})
    alvos = ["1x1-mobile","2x2-mobile","3x3-mobile","4x4-mobile","1x1-emulador","2x2-emulador","3x3-emulador","4x4-emulador","2x2-misto","3x3-misto","4x4-misto"]
    canais=[]
    for canal in ctx.guild.text_channels:
        for alvo in alvos:
            if alvo in canal.name.lower():
                canais.append(canal); break

    total_filas = len(canais) * len(VALORES)
    count=0
    for canal in canais:
        ok = await limpar_e_criar_fila(canal)
        if ok: count+=1
        await asyncio.sleep(1)

    await ctx.send(f"✅ **{count * len(VALORES)} fileiras criadas!**\nModelo: `• 1v1 Mobile • R$ X` com cor VERDE e sistema de nomes funcionando.")

bot.run(os.getenv("DISCORD_TOKEN"))
