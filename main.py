import discord
from discord import app_commands
from discord.ext import commands
import google.generativeai as genai
from gtts import gTTS
import asyncio
import os
from dotenv import load_dotenv

# تحميل البيانات السرية من ملف .env أو إعدادات السيرفر
load_dotenv()
DISCORD_TOKEN = os.getenv("MTQ2MTM0NTg5MTIwOTMxODQyMA.GVC7hO.KW416U5E6WPiM5pQ_qdo5H0oZwHZ1VlhpBr6cU")
GEMINI_KEY = os.getenv("AIzaSyAvAVXbOLCkHfy_3IeNDaZf1534Fe6r3sg")
ROLE_ID = os.getenv("1286327980938887251")

# إعداد ذكاء Gemini الاصطناعي
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-pro')

class SupportBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.voice_states = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.target_channel_id = None # لتخزين ID الغرفة المختارة

    async def setup_hook(self):
        # مزامنة أوامر الـ Slash مع سيرفرات ديسكورد
        await self.tree.sync()
        print(f"تمت مزامنة الأوامر بنجاح.")

bot = SupportBot()

def generate_audio_file(text):
    """تحويل النص إلى ملف صوتي mp3"""
    tts = gTTS(text=text, lang='ar')
    tts.save("announcement.mp3")

@bot.event
async def on_ready():
    print(f'✅ البوت يعمل الآن باسم: {bot.user}')

@bot.tree.command(name="غرفة", description="تحديد الغرفة الصوتية للدعم الفني")
@app_commands.describe(channel="اختر الغرفة الصوتية التي سيراقبها البوت")
async def set_room(interaction: discord.Interaction, channel: discord.VoiceChannel):
    bot.target_channel_id = channel.id
    await interaction.response.send_message(f"🎯 تم ضبط البوت لمراقبة الغرفة: **{channel.name}**")

@bot.event
async def on_voice_state_update(member, before, after):
    # التحقق: هل دخل عضو للغرفة المحددة؟ وهل العضو ليس البوت؟
    if after.channel and after.channel.id == bot.target_channel_id and not member.bot:
        
        # 1. إرسال منشن لرتبة الدعم في أول قناة نصية يراها البوت
        role_mention = f"<@&{ROLE_ID}>"
        for text_channel in member.guild.text_channels:
            if text_channel.permissions_for(member.guild.me).send_messages:
                await text_channel.send(f"🚨 {role_mention} | العضو {member.mention} دخل غرفة الدعم وينتظر المساعدة!")
                break

        # 2. انضمام البوت للغرفة الصوتية
        try:
            vc = await after.channel.connect()
        except discord.ClientException:
            # إذا كان البوت متصلاً بالفعل
            vc = member.guild.voice_client

        # 3. إعداد النص الذي سينطقه البوت
        script = "لا بأس نعلم ان لديكم الكثير من المشاكل ولكن انا قمت بأرسال المنشن الى قسم الدعم الفني لكي يتم معالجه مشاكلكم و نرجو ان يكون وقتكم اثمن في الاستغفار اثناء الانتظار"
        generate_audio_file(script)

        # 4. حلقة التكرار الصوتي (لا يتوقف أبداً طالما العضو موجود)
        while member.voice and member.voice.channel.id == bot.target_channel_id:
            if not vc.is_playing():
                # استخدام FFmpeg لتشغيل الصوت
                vc.play(discord.FFmpegPCMAudio("announcement.mp3"))
                
                # الانتظار حتى ينتهي المقطع الصوتي
                while vc.is_playing():
                    await asyncio.sleep(1)
                
                # وقت راحة قصير قبل إعادة الجملة
                await asyncio.sleep(2)
            else:
                await asyncio.sleep(1)

        # 5. مغادرة البوت إذا غادر العضو الغرفة ولم يتبق أحد غير البوت
        if len(after.channel.members) <= 1:
            await vc.disconnect()

# تشغيل البوت
if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)
else:
    print("❌ خطأ: لم يتم العثور على DISCORD_TOKEN في متغيرات البيئة.")
