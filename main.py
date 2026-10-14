import discord
from discord.ext import commands
import os, json, random

TOKEN = os.getenv("DISCORD_TOKEN")
VERDE = 0x00FF7F
ARQ_FILA = "filas.json"
ARQ_BLACK = "blacklist.json"

VALORES_SLUSH = ["0,70","1,00","2,00","3,00","4,00","5,00","10,00","30,00","40,00","50,00","100,00","150,00","200,00"]

def get_taxa(valor_float):
    if valor_float <= 30.00:
        return 0.50
    else:
        return 2.50

def load_json(arq):
    if not os.path.exists(arq): return {}
    try:
        with open(arq,"r") as f: return json.load(f)
    except: return {}

def save_json(arq,data):
    with open(arq,"w") as f: json.dump(data,f)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

class VerificacaoModal(discord.ui.Modal, title="Verificacao ORG SLUSH"):
    comida = discord.ui.TextInput(label="Digite: batata", placeholder="Escreva batata")
    async def on_submit(self, interaction):
        if self.comida.value.lower()!= "batata":
            await interaction.response.send_message("Falhou!", ephemeral=True); return
        await interaction.response.send_message("OK!", ephemeral=True)

class FilaView(discord.ui.View):
    def __init__(self, modo, valor_str, tipo):
        super().__init__(timeout=None)
        self.modo=modo; self.valor_str=valor_str; self.tipo=tipo
    @discord.ui.button(label="Entrar", style=discord.ButtonStyle.success)
    async def entrar(self, interaction, button):
        bl=load_json(ARQ_BLACK)
        if str(interaction.user.id) in bl:
            await interaction.response.send_message("BLACKLIST ORG SLUSH", ephemeral=True); return
        await interaction.response.send_modal(VerificacaoModal())
        filas=load_json(ARQ_FILA)
        chave=f"{self.modo}_{self.valor_str}_{self.tipo}"
        if chave not in filas: filas[chave]=[]
        if interaction.user.id not in filas[chave]:
            filas[chave].append(interaction.user.id)
            save_json(ARQ_FILA, filas)
            total_needed=int(self.modo[0])
            if len(filas[chave]) >= total_needed:
                jogs=filas[chave][:total_needed]
                filas[chave]=filas[chave][total_needed:]
                save_json(ARQ_FILA, filas)
                await criar_partida(interaction.guild, jogs, self.modo, self.valor_str)

    @discord.ui.button(label="Sair", style=discord.ButtonStyle.danger)
    async def sair(self, interaction, button):
        filas=load_json(ARQ_FILA)
        chave=f"{self.modo}_{self.valor_str}_{self.tipo}"
        if chave in filas and interaction.user.id in filas[chave]:
            filas[chave].remove(interaction.user.id)
            save_json(ARQ_FILA, filas)
        await interaction.response.send_message("Saiu da fila ORG SLUSH", ephemeral=True)

async def criar_partida(guild, jogadores, modo, valor_str):
    v_float = float(valor_str.replace(",","."))
    taxa = get_taxa(v_float)
    total_pagar = v_float + taxa
    premio = v_float * len(jogadores)

    cat = discord.utils.get(guild.categories, name="PARTIDAS SLUSH")
    if not cat: cat = await guild.create_category("PARTIDAS SLUSH")
    overw = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
    for uid in jogadores:
        m=guild.get_member(uid)
        if m: overw[m]=discord.PermissionOverwrite(view_channel=True, send_messages=True)
    ch = await guild.create_text_channel(f"partida-{random.randint(1000,9999)}", overwrites=overw, category=cat)

    mencoes = " ".join([f"<@{x}>" for x in jogadores])
    emb = discord.Embed(
        title=f"ORG SLUSH - {modo} R$ {valor_str}",
        description=(
            f"**AP:** R$ {v_float:.2f}\n"
            f"**TAXA ORG:** R$ {taxa:.2f}\n"
            f"**TOTAL A PAGAR:** R$ {total_pagar:.2f}\n\n"
            f"🏆 **PREMIO VENCEDOR:** R$ {premio:.2f}\n"
            f"🏦 **LUCRO ORG SLUSH:** R$ {taxa*len(jogadores):.2f}"
        ),
        color=VERDE
    )
    emb.set_footer(text="ORG SLUSH - VERDE OFICIAL")
    await ch.send(f"{mencoes}\nPAGUEM R$ {total_pagar:.2f} CADA E MANDEM COMPROVANTE", embed=emb)

@bot.command()
async def painel_slush(ctx):
    # CRIA TODOS DE UMA VEZ IGUAL FUSION
    for valor in VALORES_SLUSH:
        v_float=float(valor.replace(",","."))
        taxa=get_taxa(v_float)
        total=v_float+taxa
        emb=discord.Embed(
            title=f"1x1 Mobile - R$ {valor}",
            description=f"Jogadores:\nNenhum jogador na fila.\n\n💸 Pagar: R$ {total:.2f} (R$ {v_float:.2f} AP + R$ {taxa:.2f} ORG)\n🏆 Ganha: R$ {v_float*2:.2f}",
            color=VERDE
        )
        await ctx.send(embed=emb, view=FilaView("1x1", valor, "Mobile"))

@bot.event
async def on_ready():
    print(f"ORG SLUSH VERDE ON {bot.user}")

bot.run(TOKEN)
