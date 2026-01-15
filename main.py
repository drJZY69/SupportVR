import discord
from discord import app_commands
from discord.ext import commands
from google import genai # المكتبة الجديدة
from gtts import gTTS
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")
ROLE_ID = os.getenv("ROLE_ID")

# إعداد المكتبة الجديدة
client = genai.Client(api_key=GEMINI_KEY)

def get_system_prompt():
    try:
        with open("system_prompts.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "أنت موظف دعم فني هادئ."

class SupportBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.voice_states = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.target_channel_id = None

    async def setup_hook(self):
        await self.tree.sync()

bot = SupportBot()

@bot.event
async def on_ready():
    print(f"✅ تم تسجيل الدخول بنجاح باسم: {bot.user}")

@bot.tree.command(name="غرفة", description="تحديد الغرفة الصوتية")
async def set_room(interaction: discord.Interaction, channel: discord.VoiceChannel):
    bot.target_channel_id = channel.id
    await interaction.response.send_message(f"🚀 تم الربط بـ: {channel.name}")

@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and after.channel.id == bot.target_channel_id and not member.bot:
        
        # المنشن
        role_mention = f"<@&{ROLE_ID}>"
        for text_ch in member.guild.text_channels:
            if text_ch.permissions_for(member.guild.me).send_messages:
                await text_ch.send(f"🚨 {role_mention} | {member.display_name} ينتظر!")
                break

        try:
            vc = await after.channel.connect()
        except:
            vc = member.guild.voice_client

        # توليد الرد باستخدام المكتبة الجديدة
        prompt = f"{get_system_prompt()}\n\n أبلغ العضو بالصبر والاستغفار لأن الدعم قادم."
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        
        tts = gTTS(text=response.text, lang='ar')
        tts.save("msg.mp3")

        while member.voice and member.voice.channel.id == bot.target_channel_id:
            if not vc.is_playing():
                vc.play(discord.FFmpegPCMAudio("msg.mp3"))
                while vc.is_playing():
                    await asyncio.sleep(1)
                await asyncio.sleep(5)
            else:
                await asyncio.sleep(1)

        if len(after.channel.members) <= 1:
            await vc.disconnect()

bot.run(DISCORD_TOKEN)
