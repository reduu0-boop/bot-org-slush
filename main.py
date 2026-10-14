import discord
from discord.ext import commands
import json, os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

ARQ = "filas.json"

def load_filas():
    if not os.path.exists(ARQ): return {}
    try:
        with open(ARQ, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return {}

def save_filas(d):
    with open(ARQ, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)

filas = load_filas()


class FilaView(discord.ui.View):
    def __init__(self, canal, valor):
        super().__init__(timeout=None)
        self.canal = canal
        self.valor = valor

    def get_desc(self):
        lista = filas.get(self.canal, [])
        if not lista: return "🔹 Jogadores:\nNenhum jogador na fila."
        linhas = [f"{i+1}º - <@{u}>" for i, u in enumerate(lista)]
        return "🔹 Jogadores:\n" + "\n".join(linhas)

    @discord.ui.button(label="Sair do infinito", style=discord.ButtonStyle.secondary)
    async def infinito_sair(self, inter: discord.Interaction):
        filas.setdefault(self.canal, []).remove(inter.user.id)
        save_filas(filas)
        emb = inter.message.embeds[0]
        emb.description = self.get_desc()
        await inter.response.edit_message(embed=emb, view=self)

    @discord.ui.button(label="Entrar Normal", style=discord.ButtonStyle.secondary)
    async def normal(self, inter: discord.Interaction):
        filas.setdefault(self.canal, []).append(inter.user.id)
        save_filas(filas)
        emb = inter.message.embeds[0]
        emb.description = self.get_desc()
        await inter.response.edit_message(embed=emb, view=self)

    @discord.ui.button(label="Sair", style=discord.ButtonStyle.danger)
    async def sair(self, inter: discord.Interaction):
        uid = inter.user.id
        if self.canal in filas and uid in filas[self.canal]:
            filas[self.canal].remove(uid)
            save_filas(filas)
        emb = inter.message.embeds[0]
        emb.description = self.get_desc()
        await inter.response.edit_message(embed=emb, view=self)


@bot.event
async def on_ready():
    print("ok")


@bot.command()
async def painel_todas(ctx):
    await ctx.message.delete()
    for canal in ctx.guild.text_channels:
        if "💥" not in canal.name: continue
        nome = canal.name.lower()
        if "1v1" not in nome and "1 vs 1" not in nome: continue
        try:
            valor = canal.name.split("💥")[-1].replace("•", "").strip()
        except: valor = "0"
        if "mobile" in nome.lower(): titulo = f"🏆 1v1 Mobile - R${valor}"
        else: titulo = f"🏆 1v1 - R${valor}"

        filas.setdefault(canal.id, [])
        desc = "🔹 Jogadores:\nNenhum jogador na fila."
        if filas[canal.id]:
            desc = "🔹 Jogadores:\n" + "\n".join([f"{i+1}º - <@{u}>" for i, u in enumerate(filas[canal.id])])

        emb = discord.Embed(title=titulo, description=desc, color=0x2B2D31)
        await canal.send(embed=emb, view=FilaView(canal.id, valor))


bot.run(os.getenv("DISCORD_TOKEN"))
