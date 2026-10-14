import discord
from discord.ext import commands
import json, os

TOKEN = os.getenv("DISCORD_TOKEN") or "SEU_TOKEN"
COR = 0x2B2D31
ARQ = "filas.json"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

def load():
    if not os.path.exists(ARQ):
        return {}
    try:
        with open(ARQ,"r",encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save(d):
    with open(ARQ,"w",encoding="utf-8") as f:
        json.dump(d,f,indent=2,ensure_ascii=False)

async def criar_sala(guild,ids,modo,valor):
    overwrites={
        guild.default_role:
        discord.PermissionOverwrite(view_channel=False)
    }
    for i in ids:
        m=guild.get_member(i)
        if m:
            overwrites[m]=discord.PermissionOverwrite(
                view_channel=True,send_messages=True
            )
    overwrites[guild.me]=discord.PermissionOverwrite(
        view_channel=True,manage_channels=True
    )
    cat=discord.utils.get(guild.categories,name="PARTIDAS")
    if not cat:
        cat=await guild.create_category("PARTIDAS")
    canal=await guild.create_text_channel(
        f"{modo}-{valor}",overwrites=overwrites,category=cat
    )
    return canal

class Painel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="4x4 R$5",
        style=discord.ButtonStyle.primary,
        custom_id="criar:4x4_5"
    )
    async def b1(self,interaction,button):
        await self.criar(interaction,"4x4","5")

    @discord.ui.button(
        label="4x4 R$10",
        style=discord.ButtonStyle.primary,
        custom_id="criar:4x4_10"
    )
    async def b2(self,interaction,button):
        await self.criar(interaction,"4x4","10")

    @discord.ui.button(
        label="6x6 R$5",
        style=discord.ButtonStyle.success,
         @discord.ui.button(
        label="6x6 R$10",
        style=discord.ButtonStyle.success,
        custom_id="criar:6x6_10"
    )
    async def b4(self,interaction,button):
        await self.criar(interaction,"6x6","10")

    async def criar(self,interaction,modo,valor):
        await interaction.response.defer(ephemeral=True)
        filas=load()
        chave=f"{modo}_{valor}"
        if chave in filas and len(filas[chave])>0:
            await interaction.followup.send(
                "Ja tem fila aberta!",ephemeral=True
            )
            return
        emb=discord.Embed(
            title=f"{modo} R$ {valor}",
            description="Fila aberta! Clique no gelo",
            color=COR
        )
        await interaction.followup.send(
            embed=emb,view=ViewFila(modo,valor)
        )

class ViewFila(discord.ui.View):
    def __init__(self,modo,valor):
        super().__init__(timeout=None)
        self.modo=modo
        self.valor=valor

    @discord.ui.button(
        label="Gelo INF",
        style=discord.ButtonStyle.secondary
    )
    async def inf(self,interaction,button):
        await self.entrar(interaction,"INF")

    @discord.ui.button(
        label="Gelo Normal",
        style=discord.ButtonStyle.secondary
    )
    async def nor(self,interaction,button):
        await self.entrar(interaction,"Normal")

    @discord.ui.button(
        label="Sair",
        style=discord.ButtonStyle.danger
    )
    async def sair(self,interaction,button):
        filas=load()
        chave=f"{self.modo}_{self.valor}"
        uid=interaction.user.id
        if chave in filas and uid in filas[chave]:
            filas[chave].remove(uid)
            save(filas)
        await interaction.response.send_message(
            "Saiu da fila",ephemeral=True
        )

    async def entrar(self,interaction,gelo):
        filas=load()
        chave=f"{self.modo}_{self.valor}"
        if chave not in filas:
            filas[chave]=[]
        uid=interaction.user.id
        if uid in filas[chave]:
            await interaction.response.send_message(
                "Ja ta na fila",ephemeral=True
            )
            return
        filas[chave].append(uid)
        save(filas)
        await interaction.response.send_message(
            f"Entrou! {gelo}",ephemeral=True
        )
        qtd=len(filas[chave])
        total=4 if "4x4" in self.modo else 6
        if qtd>=total:
            jogadores=filas[chave][:total]
            filas[chave]=filas[chave][total:]
            save(filas)
            canal=await criar_sala(
                interaction.guild,jogadores,
                self.modo,self.valor
            )
            txt=" ".join([f"<@{x}>" for x in jogadores])
            await canal.send(
                f"{txt} Partida {self.modo} R${self.valor}"
            )
            try:
                await interaction.message.delete()
            except:
                pass

@bot.event
async def on_ready():
    print(f"Logado {bot.user}")
    bot.add_view(Painel())

@bot.command()
async def painel(ctx):
    emb=discord.Embed(
        title="PAINEL APOSTAS",
        description="Clique pra criar",
        color=COR
    )
    await ctx.send(embed=emb,view=Painel())

@bot.command()
async def limpar_filas(ctx):
    save({})
    await ctx.send("Filas limpas!")

bot.run(TOKEN)
        custom_id="criar:6x6_5"
    )
    async def b3(self,interaction,button):
        await self.criar(interaction,"6x6","5")
