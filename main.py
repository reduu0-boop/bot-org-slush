import discord
from discord.ext import commands
import json, os

TOKEN = "SEU_TOKEN"
COR = 0x2B2D31
ARQ = "filas.json"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(
 command_prefix="!",
 intents=intents
)

def load():
 if not os.path.exists(ARQ):
  return {}
 with open(ARQ,"r") as f:
  try:
   return json.load(f)
  except:
   return {}

def save(d):
 with open(ARQ,"w") as f:
  json.dump(d,f,indent=2)

async def criar_sala(guild, ids, modo, valor):
 over = {
  guild.default_role:
   discord.PermissionOverwrite(
    view_channel=False
   )
 }
 for i in ids:
  m = guild.get_member(i)
  if m:
   over[m] = discord.PermissionOverwrite(
    view_channel=True,
    send_messages=True
   )
 over[guild.me] = discord.PermissionOverwrite(
  view_channel=True,
  manage_channels=True
 )
 cat = discord.utils.get(
  guild.categories,
  name="PARTIDAS"
 )
 if not cat:
  cat = await guild.create_category(
   "PARTIDAS"
  )
 nome = f"{modo}-{valor}"
 canal = await guild.create_text_channel(
  nome,
  overwrites=over,
  category=cat
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
 async def b1(self,it,bt):
  await self.criar(it,"4x4","5")

 @discord.ui.button(
  label="4x4 R$10",
  style=discord.ButtonStyle.primary,
  custom_id="criar:4x4_10"
 )
 async def b2(self,it,bt):
  await self.criar(it,"4x4","10")
      async def criar(self,it,modo,valor):
  await it.response.defer(ephemeral=True)
  filas = load()
  chave = f"{modo}_{valor}"
  if chave in filas and len(filas[chave])>0:
   await it.followup.send(
    "Ja tem fila aberta!",
    ephemeral=True
   )
   return
  emb = discord.Embed(
   title=f"{modo} R$ {valor}",
   description="Fila aberta!",
   color=COR
  )
  await it.followup.send(
   embed=emb,
   view=ViewFila(modo,valor)
  )

class ViewFila(discord.ui.View):
 def __init__(self,modo,valor):
  super().__init__(timeout=None)
  self.modo=modo
  self.valor=valor

 @discord.ui.button(
  label="Gelo INF",
  style=discord.ButtonStyle.gray,
  custom_id="g:inf"
 )
 async def inf(self,it,bt):
  await self.entrar(it,"INF")

 @discord.ui.button(
  label="Gelo Normal",
  style=discord.ButtonStyle.gray,
  custom_id="g:normal"
 )
 async def nor(self,it,bt):
  await self.entrar(it,"Normal")

 @discord.ui.button(
  label="Sair",
  style=discord.ButtonStyle.danger,
  custom_id="g:sair"
 )
 async def sair(self,it,bt):
  filas=load()
  chave=f"{self.modo}_{self.valor}"
  uid=it.user.id
  if chave in filas:
   if uid in filas[chave]:
    filas[chave].remove(uid)
    save(filas)
  await it.response.send_message(
   "Saiu da fila",
   ephemeral=True
  )

 async def entrar(self,it,gelo):
  filas=load()
  chave=f"{self.modo}_{self.valor}"
  if chave not in filas:
   filas[chave]=[]
  uid=it.user.id
  if uid in filas[chave]:
   await it.response.send_message(
    "Ja ta na fila",
    ephemeral=True
   )
   return
  filas[chave].append(uid)
  save(filas)
  await it.response.send_message(
   f"Entrou! {gelo}",
   ephemeral=True
  )
  qtd=len(filas[chave])
  total=4 if "4x4" in self.modo else 6
  if qtd>=total:
   jogadores=filas[chave][:total]
   filas[chave]=filas[chave][total:]
   save(filas)
   canal=await criar_sala(
    it.guild,
    jogadores,
    self.modo,
    self.valor
   )
   txt=" ".join([f"<@{x}>" for x in jogadores])
   await canal.send(
    f"{txt}\nPartida {self.modo} R${self.valor} fechada!"
   )
   try:
    await it.message.delete()
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
