import discord
from discord import app_commands
from discord.ext import commands
import google.generativeai as genai
from gtts import gTTS
import asyncio
import os
from dotenv import load_dotenv

# تحميل البيانات السرية
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")
ROLE_ID = os.getenv("ROLE_ID")

# إعداد ذكاء Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-pro')

# وظيفة لقراءة ملف التوجيهات (System Prompt)
def get_system_prompt():
    try:
        with open("system_prompts.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "أنت موظف دعم فني هادئ ووقور."

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

def generate_audio_file(text):
    tts = gTTS(text=text, lang='ar')
    tts.save("announcement.mp3")

@bot.tree.command(name="غرفة", description="تحديد الغرفة الصوتية للدعم الفني")
async def set_room(interaction: discord.Interaction, channel: discord.VoiceChannel):
    bot.target_channel_id = channel.id
    await interaction.response.send_message(f"🎯 تم ضبط البوت لمراقبة الغرفة: **{channel.name}**")

@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and after.channel.id == bot.target_channel_id and not member.bot:
        
        # 1. إرسال منشن في القنوات النصية
        role_mention = f"<@&{ROLE_ID}>"
        for text_channel in member.guild.text_channels:
            if text_channel.permissions_for(member.guild.me).send_messages:
                await text_channel.send(f"🚨 {role_mention} | العضو {member.mention} ينتظر في غرفة الدعم!")
                break

        # 2. انضمام البوت صوتياً
        try:
            vc = await after.channel.connect()
        except discord.ClientException:
            vc = member.guild.voice_client

        # 3. استخدام Gemini لتوليد النص بناءً على ملف system_prompts.txt
        system_instructions = get_system_prompt()
        user_request = (
            "أخبر العضو أننا نعلم بمشكلته وأن الدعم الفني قادم، "
            "وانصحه بالاستغفار أثناء الانتظار. اجعل النص قريباً من: "
            "'لا بأس نعلم ان لديكم الكثير من المشاكل ولكن انا قمت بأرسال المنشن الى قسم الدعم الفني لكي يتم معالجه مشاكلكم و نرجو ان يكون وقتكم اثمن في الاستغفار اثناء الانتظار'"
        )
        
        # استدعاء Gemini لإنشاء نص متجدد بنفس المعنى
        response = model.generate_content(f"{system_instructions}\n\nطلب العضو: {user_request}")
        final_text = response.text if response.text else "نرجو الانتظار، الدعم قادم، استثمر وقتك بالاستغفار."

        # تحويل النص المولد من Gemini إلى صوت
        generate_audio_file(final_text)

        # 4. حلقة التكرار الصوتي
        while member.voice and member.voice.channel.id == bot.target_channel_id:
            if not vc.is_playing():
                vc.play(discord.FFmpegPCMAudio("announcement.mp3"))
                while vc.is_playing():
                    await asyncio.sleep(1)
                await asyncio.sleep(5) # استراحة قصيرة قبل الإعادة
            else:
                await asyncio.sleep(1)

        if len(after.channel.members) <= 1:
            await vc.disconnect()

bot.run(DISCORD_TOKEN)
