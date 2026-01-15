import discord
from discord import app_commands
from discord.ext import commands
from google import genai
from gtts import gTTS
import asyncio
import os
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# --- إعداد خادم الويب لـ UptimeRobot ---
web_app = Flask('')

@web_app.route('/')
def home():
    return "Bot is Online and Running 24/7!"

def run_web():
    # المنصات مثل Railway تستخدم بورت 8080 تلقائياً
    web_app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- تحميل الإعدادات ---
load_dotenv()
# ملاحظة: سنستخدم الأسماء التي وضعتها أنت
TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_KEY")
ROLE_ID = os.getenv("ROLE_ID")

# إعداد مكتبة Gemini الجديدة
client = genai.Client(api_key=GEMINI_API_KEY)

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.voice_states = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.target_channel_id = None

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ تم مزامنة أوامر السلاش بنجاح.")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"✅ تم تسجيل الدخول باسم: {bot.user}")

@bot.tree.command(name="غرفة", description="تحديد الغرفة الصوتية التي سيراقبها البوت")
@app_commands.describe(channel="اسم القناة الصوتية")
async def set_room(interaction: discord.Interaction, channel: discord.VoiceChannel):
    bot.target_channel_id = channel.id
    await interaction.response.send_message(f"🚀 تم ربط البوت بنجاح بغرفة: {channel.name}")

@bot.event
async def on_voice_state_update(member, before, after):
    # التحقق من دخول العضو للغرفة المحددة وأن العضو ليس البوت
    if after.channel and after.channel.id == bot.target_channel_id and not member.bot:
        
        # 1. إرسال منشن للرتبة في أول قناة نصية يجدها البوت
        role_mention = f"<@&{ROLE_ID}>"
        for channel in member.guild.text_channels:
            if channel.permissions_for(member.guild.me).send_messages:
                await channel.send(f"⚠️ تنبيه {role_mention}: العضو {member.mention} دخل غرفة الدعم!")
                break

        # 2. دخول البوت صوتياً
        try:
            vc = await after.channel.connect()
        except discord.ClientException:
            vc = member.guild.voice_client

        # 3. توليد الرد من Gemini
        prompt = (
            "أنت موظف دعم فني. قل للعضو بأسلوب لطيف: "
            "لا بأس نعلم ان لديكم الكثير من المشاكل ولكن انا قمت بأرسال المنشن الى قسم الدعم الفني "
            "لكي يتم معالجه مشاكلكم و نرجو ان يكون وقتكم اثمن في الاستغفار اثناء الانتظار"
        )
        
        try:
            response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            message_text = response.text
        except:
            message_text = "لا بأس، الدعم قادم، استثمر وقتك في الاستغفار."

        # 4. تحويل النص لصوت وتكراره
        tts = gTTS(text=message_text, lang='ar')
        tts.save("support.mp3")

        while member.voice and member.voice.channel.id == bot.target_channel_id:
            if not vc.is_playing():
                vc.play(discord.FFmpegPCMAudio("support.mp3"))
                while vc.is_playing():
                    await asyncio.sleep(1)
                await asyncio.sleep(2) # انتظار بسيط قبل الإعادة
            else:
                await asyncio.sleep(1)

        # الخروج إذا غادر العضو
        if len(after.channel.members) <= 1:
            await vc.disconnect()

if __name__ == "__main__":
    keep_alive() # تشغيل خادم الويب لـ UptimeRobot
    bot.run(TOKEN)
