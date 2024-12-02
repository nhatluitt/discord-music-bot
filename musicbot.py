import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
import random
import emoji
import requests
from io import BytesIO
from PIL import Image
from discord.ext import commands
import asyncio
from gtts import gTTS
from pydub import AudioSegment
import os
import logging
import re



# Tạo một instance của bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
bot = commands.Bot(command_prefix='?', intents=intents, help_command=None)


intents.messages = True



# Cấu hình cho yt_dlp
youtube_dl.utils.bug_reports_message = lambda: ''

ffmpeg_options = {
    'options': '-vn -loglevel error'
}

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    

# trạng thái hoạt động của bot
# @bot.event
# async def on_ready():
#     await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.listening, name='?help | Ponyo')) 

# idle: ngủ
# dnd: bận
@bot.command(name='sleep', help='Trả về "bot ngủ"')
async def sleep(ctx):
    # Thay 1234567890 bằng ID của chủ bot
    owner_id = 1214520618939318283
    if ctx.author.id != owner_id:
        await ctx.send("Chỉ có chủ bot mới có thể sử dụng lệnh này.")
        return

    await bot.change_presence(status=discord.Status.idle, activity=discord.Activity(type=discord.ActivityType.listening, name='?help | Ponyo'))
    await ctx.message.delete()






@bot.command(name='dnd', help='Trả về "bot ban"')
async def dnd(ctx):
    # Thay 1234567890 bằng ID của bạn
    owner_id = 1214520618939318283
    if ctx.author.id != owner_id:
        await ctx.send("Chỉ có chủ bot mới có thể sử dụng lệnh này.")
        return

    await bot.change_presence(status=discord.Status.dnd, activity=discord.Activity(type=discord.ActivityType.listening, name='?help | Ponyo'))
    await ctx.message.delete()


@bot.command(name='off', help='Chuyển bot sang trạng thái offline')
async def offline(ctx):
    # Thay 1234567890 bằng ID của bạn
    owner_id = 1214520618939318283
    if ctx.author.id != owner_id:
        await ctx.send("Chỉ có chủ bot mới có thể sử dụng lệnh này.")
        return

    await bot.change_presence(status=discord.Status.offline)
    # await ctx.send("Bot đã chuyển sang trạng thái offline.")
    await ctx.message.delete()






@bot.command(name='join', help='Bot sẽ tham gia vào kênh thoại')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send(f'{ctx.message.author.name} không ở trong kênh thoại')
        return
    else:
        channel = ctx.message.author.voice.channel

    await channel.connect()



@bot.command(name='volume', help='Thay đổi âm lượng')
async def volume(ctx, volume: int):
    if ctx.voice_client is None:
        return await ctx.send("Bot không ở trong kênh thoại.")
    
    ctx.voice_client.source.volume = volume / 100
    await ctx.send(f'Âm lượng đã được thay đổi thành **{volume}%**')

@bot.command(name='leave', help='Bot sẽ rời khỏi kênh thoại')
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
    else:
        await ctx.send("Bot không ở trong kênh thoại")

song_queue = {}
loop_state = {}
autoplay_state = {}

async def play_next(ctx):
    guild_id = ctx.message.guild.id
    voice_client = ctx.message.guild.voice_client
    
    if guild_id in song_queue and song_queue[guild_id]:
        next_song = song_queue[guild_id].pop(0)
        await play(ctx, next_song['url'], is_next=True)
    elif loop_state.get(guild_id, False):
        # Lặp lại bài hát hiện tại
        if voice_client and voice_client.is_playing():
            current_title = voice_client.source.title
            search_url = f"ytsearch:{current_title}"
            try:
                next_video = await YTDLSource.from_url(search_url, loop=bot.loop, stream=True)
                await play(ctx, next_video.url, is_next=True)
            except Exception as e:
                print(f"Loop error: {e}")
                await ctx.send("Không thể lặp lại bài hát.")
    elif autoplay_state.get(guild_id, False):
        # Chế độ autoplay
        current_voice_client = ctx.message.guild.voice_client
        if current_voice_client and current_voice_client.source:
            current_title = current_voice_client.source.title
            search_url = f"ytsearch:{current_title} tiếp theo"
            try:
                next_video = await YTDLSource.from_url(search_url, loop=bot.loop, stream=True)
                await play(ctx, next_video.url, is_next=True)
            except Exception as e:
                print(f"Autoplay error: {e}")
                await ctx.send("Không thể tự động phát bài hát tiếp theo.")


@bot.command(name='play', aliases=['p'], help='Phát nhạc từ YouTube')
async def play(ctx, *urls, is_next=False):
    try:
        server = ctx.message.guild
        voice_channel = server.voice_client

        if not voice_channel or not voice_channel.is_connected():
            await ctx.send("Bot chưa tham gia vào kênh thoại. Sử dụng lệnh ?join để tham gia.")
            return

        if not is_next and voice_channel.is_playing():
            if ctx.message.guild.id not in song_queue:
                song_queue[ctx.message.guild.id] = []
            for url in urls:
                data = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
                song_queue[ctx.message.guild.id].append({'title': data.title, 'url': url})
            await ctx.send(f'Bài hát đã được thêm vào danh sách: {", ".join([song["title"] for song in song_queue[ctx.message.guild.id]])}')
            
            return

        async with ctx.typing():
            player = await YTDLSource.from_url(urls[0], loop=bot.loop, stream=True)
            voice_channel.play(player, after=lambda e: bot.loop.create_task(play_next(ctx)) if not e else print(f"Player error: {e}"))

        await ctx.send(f'**Đang phát:** {player.title}')

        if len(urls) > 1:
            if ctx.message.guild.id not in song_queue:
                song_queue[ctx.message.guild.id] = []
            for url in urls[1:]:
                data = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
                song_queue[ctx.message.guild.id].append({'title': data.title, 'url': url})
    except Exception as e:
        print(f'Có lỗi xảy ra: {e}')  # Bạn có thể thay bằng logging.error() để log chi tiết hơn
        await ctx.send(f'Có lỗi xảy ra: {str(e)}')


# Hàm play_next để phát bài hát tiếp theo trong hàng đợi
async def play_next(ctx):
    server = ctx.message.guild
    voice_channel = server.voice_client

    # Kiểm tra nếu bot đã rời khỏi kênh thoại hoặc không còn kết nối
    if not voice_channel or not voice_channel.is_connected():
        await ctx.send("Bot đã rời khỏi kênh thoại hoặc không còn kết nối.")
        return

    if song_queue[ctx.message.guild.id]:
        next_song = song_queue[ctx.message.guild.id].pop(0)
        player = await YTDLSource.from_url(next_song['url'], loop=bot.loop, stream=True)
        voice_channel.play(player, after=lambda e: bot.loop.create_task(play_next(ctx)) if not e else print(f"Player error: {e}"))
        await ctx.send(f'**Đang phát:** {player.title}')
    else:
        await ctx.send("Danh sách phát đã hết.")



@bot.command(name='pause', help='Tạm dừng phát nhạc')
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.pause()
    else:
        await ctx.send("Không có bài hát nào đang phát")

@bot.command(name='resume', help='Tiếp tục phát nhạc')
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        voice_client.resume()
    else:
        await ctx.send("Không có bài hát nào đang tạm dừng")

@bot.command(name='stop', help='Dừng phát nhạc')
async def stop(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()
        guild_id = ctx.message.guild.id
        if guild_id in song_queue:
            song_queue[guild_id] = []
    else:
        await ctx.send("Không có bài hát nào đang phát")

@bot.command(name='loop', help='Bật hoặc tắt chế độ lặp lại danh sách bài hát')
async def loop(ctx):
    guild_id = ctx.message.guild.id
    loop_state[guild_id] = not loop_state.get(guild_id, False)
    await ctx.send(f"Chế độ lặp danh sách:   {'**đã bật**' if loop_state[guild_id] else '**đã tắt**'}.")


@bot.command(name='autoplay', help='Bật hoặc tắt chế độ phát tự động bài hát tiếp theo dựa trên tiêu đề hiện tại')
async def autoplay(ctx):
    guild_id = ctx.message.guild.id
    autoplay_state[guild_id] = not autoplay_state.get(guild_id, False)
    await ctx.send(f"Chế độ phát tự động {'đã bật' if autoplay_state[guild_id] else 'đã tắt'}.")

@bot.command(name='queue', aliases=['q'], help='Hiển thị danh sách bài hát hiện tại')
async def queue(ctx):
    guild_id = ctx.message.guild.id
    if guild_id in song_queue and song_queue[guild_id]:
        queue_list = [f"{index + 1}. {item['title']}" for index, item in enumerate(song_queue[guild_id])]
        await ctx.send(f"**Danh sách bài hát hiện tại**:\n" + "\n".join(queue_list))
    else:
        await ctx.send("Danh sách bài hát trống.")

@bot.command(name='skip', aliases=['s'], help='Bỏ qua bài hát hiện tại và phát bài tiếp theo trong hàng đợi')
async def skip(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()
        await play_next(ctx)
    else:
        await ctx.send("Không có bài hát nào đang phát để bỏ qua.")

@bot.command(name='cf', help='Tạo kết quả ngẫu nhiên giữa "mặt úp" và "mặt ngửa"')
async def flip_coin(ctx):
    result = random.choice(['mặt úp', 'mặt ngửa'])
    await ctx.send(f'**{result}**')


@bot.command(name='thinh', help='Tạo kết quả ngẫu nhiên giữa "thính"')
async def flip_coin(ctx):
    result = random.choice(['Trời xanh mây trắng, nắng vàng. Em xinh em đẹp, khiến chàng vấn vương.',
                            'Hôm nay trời đẹp nắng êm. Em đi ngang qua, khiến tim anh lộn nhào.',
                            'Cà phê đen đắng, trà sữa ngọt thanh. Em mỉm cười, anh biết tình tan.',
                            'Bánh mì giòn tan, pate béo ngậy. Có em bên cạnh, hạnh phúc bấy nhiêu.',
                            'Em đây không thích cạnh tranh. Em đây chỉ thích cạnh anh thôi à.',
                            'Người ta gọi em là thánh yêu nhưng họ đâu biết là em thiếu anh.',
                            'Nếu anh cảm lạnh là do gió nhưng anh cảm nắng chắc chắn là do em. ',
                            'Trời đổ mưa rồi, sao em còn chưa đổ anh?',
                            'Em có biết sao da anh đen không? Vì anh mải mê ngắm nụ cười tỏa nắng của em đấ',
                            'Trăng lên đỉnh núi trăng tà. Em yêu anh thật hay là yêu chơi?',
                            'Bình minh thì ở phía đông, còn bình yên thì ở phía anh.',
                            'Bồ công anh chỉ bay khi có gió. Anh chỉ cười khi nơi đó có em.',
                            'Cười là phải thế mà thề là phải cưới đó nha.',
                            'Dạo này anh thấy người yếu. Chắc tại anh thiếu người ấy.',
                            'Anh đừng có sầu dù đầu có sừng.',
                            'HipHop never die. Yêu anh never sai.',
                            'Nam châm thì từ tính, còn chúng mình thì tình tứ nha.',
                            'Request là yêu cầu, còn tớ thì yeu cau (yêu cậu).',
                            'Em chẳng muốn hơn ai. Em chỉ muốn hon anh thoi (hôn anh thôi).',
                            'Gần mực thì đen, gần anh thì em thấy hạnh phúc.',
                            'Em có một cái bánh, anh có hai cái bánh. Anh hon (hôn) em một cái nha.',
                            'Nếu Trái Đất ngừng quay và cô dâu 8 tuổi ngừng phát sóng thì khi đó, em ngừng yêu anh.',
                            'Nắng kia làm má em hồng, anh đây có chịu làm chồng em không?',
                            'Em hãy gọi anh là hình tròn. “Ủa tại sao nhỉ?”. Tại trong hình tròn luôn có Tâm.',
                            'Người ta thì thích thành đạt. Em đây chỉ thích Thành hôn.',
                            'Cha mẹ em sinh em khéo quá. Vì gương mặt em giống hệt con dâu của mẹ anh.',
                            
                            ])
    await ctx.send(f'**{result}**')


@bot.command(name='random', aliases=['r'], help='Tạo một số ngẫu nhiên trong khoảng từ start đến end')
async def random_number(ctx, end: int, start: int = 1):
    
    if start >= end:
        await ctx.send('Tham số không hợp lệ! Giá trị bắt đầu phải nhỏ hơn giá trị kết thúc.')
    else:
        result = random.randint(start, end)
        await ctx.send(f'Số ngẫu nhiên của bạn là: **{result}**')

@bot.command(name='ping', help='Trả về "pong"')
async def ping(ctx):
    await ctx.send('pong')

@bot.command(name='pong', help='Trả về "ping"')
async def pong(ctx):
    await ctx.send('ping')


@bot.command(name='hug', help='Trả về "hug"')
async def pong(ctx):
    await ctx.send('https://cdn.weeb.sh/images/Hk3ox0tYW.gif')
    await ctx.message.delete()

@bot.command(name='kẻ', help='Trả về "https://cdn.discordapp.com/attachments/1053799649938505889/1094855782379565116/rainbow.gif?ex=66a484e7&is=66a33367&hm=9d37d188a496e46113a21901c0b5a4acc733b218d32f4f6dd61c04f1b1a16690&"')
async def pong(ctx):
    await ctx.send('https://cdn.discordapp.com/attachments/1053799649938505889/1094855782379565116/rainbow.gif?ex=66a484e7&is=66a33367&hm=9d37d188a496e46113a21901c0b5a4acc733b218d32f4f6dd61c04f1b1a16690&')
    await ctx.message.delete()

@bot.command(name='help', help='Hiển thị danh sách các lệnh')
async def help_command(ctx):
    help_text = """ 
    **Danh sách các lệnh:**
    **?join** - Bot sẽ tham gia vào kênh thoại.
    **?leave** - Bot sẽ rời khỏi kênh thoại.
    **?play [URL]** - Phát nhạc từ YouTube.
    **?pause** - Tạm dừng phát nhạc.    
    **?resume** - Tiếp tục phát nhạc.
    **?stop** - Dừng phát nhạc.
    **?loop** - Bật hoặc tắt chế độ lặp lại danh sách bài hát.
    **?autoplay** - Bật hoặc tắt chế độ phát tự động bài hát tiếp theo dựa trên tiêu đề hiện tại.
    **?queue** - Hiển thị danh sách bài hát hiện tại.
    **?volume** - Tăng giảm âm lượng.
    **?skip** - Bỏ qua bài hát hiện tại và phát bài tiếp theo trong hàng đợi.
    **?cf** - Tạo kết quả ngẫu nhiên giữa "mặt úp" và "mặt ngửa".
    **?random - r [start] [end]** - Tạo một số ngẫu nhiên trong khoảng từ start đến end.
    **?tx** - chơi tài xỉu
    **?bc** - chơi bầu cua tôm cua
    **?ping** - Trả về "pong".
    **?pong** - Trả về "ping".
    **?kẻ** - Trả về "dòng kẻ".
    **?say** - Giọng chị google đọc tin nhắn.(Bot sẽ không đọc được tin nhắn khi đang phát nhạc)
    **?giveaway <thời gian (ví dụ: 1h30m)> <số người thắng> <phần thưởng>** - Tạo giveaway

    **BOT SẼ CẬP NHẬT THÊM TRONG THỜI GIAN TỚI**
    """
    await ctx.send(help_text)

# bầu cua
bau_cua_dict = {
    "https://cdn.discordapp.com/emojis/1035685221078683658.webp?size=128&quality=lossless": "**Bầu**",
    "https://cdn.discordapp.com/emojis/1035685224249565204.webp?size=128&quality=lossless": "**Cua**",
    "https://cdn.discordapp.com/emojis/1035685235603542078.webp?size=128&quality=lossless": "**Tôm**",
    "https://cdn.discordapp.com/emojis/1035685227890233424.webp?size=128&quality=lossless": "**Cá**",
    "https://cdn.discordapp.com/emojis/1035685233099558923.webp?size=128&quality=lossless": "**Nai**",
    "https://cdn.discordapp.com/emojis/1035685230222266451.webp?size=128&quality=lossless": "**Gà**"
}


@bot.command(name='bc', help='Trả về ngẫu nhiên 3 emoji hoặc hình ảnh cho trò chơi Bầu Cua')
async def ke(ctx):
    selected_items = random.sample(list(bau_cua_dict.keys()), 3)  # Chọn ngẫu nhiên 3 mục từ danh sách
    selected_names = [bau_cua_dict[item] for item in selected_items]  # Lấy tên tương ứng cho mỗi mục

    # Tải và xử lý hình ảnh
    images = []
    for item in selected_items:
        response = requests.get(item)
        img = Image.open(BytesIO(response.content))
        img = img.resize((50, 50))  # Thay đổi kích thước ảnh thành 50x50
        images.append(img)

    # Tạo ảnh ghép ngang với khoảng cách giữa các ảnh
    padding = 10
    total_width = sum(img.width for img in images) + padding * (len(images) - 1)
    max_height = max(img.height for img in images)
    new_image = Image.new('RGBA', (total_width, max_height))

    x_offset = 0
    for img in images:
        new_image.paste(img, (x_offset, 0))
        x_offset += img.width + padding

    # Lưu ảnh ghép vào bộ nhớ tạm
    with BytesIO() as image_binary:
        new_image.save(image_binary, 'PNG')
        image_binary.seek(0)
        await ctx.send(file=discord.File(fp=image_binary, filename='bau_cua.png'))

    # Gửi kết quả dạng tên với dấu chấm giữa các tên
    name_message = "Kết quả là: " + " • ".join(selected_names)
    await ctx.send(name_message)

    

dice_images = {
    1: "https://cdn.discordapp.com/emojis/1031866523708555335.webp?size=128&quality=lossless",
    2: "https://cdn.discordapp.com/emojis/1031866428812439562.webp?size=128&quality=lossless",
    3: "https://cdn.discordapp.com/emojis/1031866398923816982.webp?size=128&quality=lossless",
    4: "https://cdn.discordapp.com/emojis/1031866367089066044.webp?size=128&quality=lossless",
    5: "https://cdn.discordapp.com/emojis/1031866336835534868.webp?size=128&quality=lossless",
    6: "https://cdn.discordapp.com/emojis/1031866305663483944.webp?size=128&quality=lossless"
}

# URL của GIF lắc xúc xắc
shaking_gif_url = "https://cdn.discordapp.com/emojis/1031872079500427324.gif?size=128&quality=lossless"

# Khởi tạo bot
# Chức năng để chuyển đổi giá trị xúc xắc sang chữ
def dice_to_text(dice):
    text = ["", "**Một**", "**Hai**", "**Ba**", "**Bốn**", "**Năm**", "**Sáu**"]
    return text[dice]

@bot.event
async def on_ready():
    print(f'Đã đăng nhập với tên {bot.user}')
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.listening, name='?help | Ponyo')) 
    

@bot.command(name='tx', help='Chơi trò chơi Tài Xỉu')
async def tai_xiu(ctx):
    dice = [random.randint(1, 6) for _ in range(3)]  # Đổ 3 con xúc xắc
    total = sum(dice)
    
    # Xác định kết quả là Tài hay Xỉu
    result_tai_xiu = "Tài" if total >= 11 else "Xỉu"
    # Xác định kết quả là Chẵn hay Lẻ
    result_chan_le = "Chẵn" if total % 2 == 0 else "Lẻ"

    # Tạo thông báo kết quả
    dice_text = ' • '.join(dice_to_text(die) for die in dice)
    result_message = f'Kết quả là: {dice_text}'

    # Tạo danh sách các hình ảnh xúc xắc để gửi
    images = []
    for die in dice:
        # Tải hình ảnh từ URL
        response = requests.get(dice_images[die])
        img = Image.open(BytesIO(response.content))
        
        # Thay đổi kích thước ảnh thành 50x50
        img = img.resize((50, 50), Image.LANCZOS)
        images.append(img)

    # Tạo ảnh ghép ngang với các hình ảnh xúc xắc
    padding = 10  # Khoảng cách giữa các hình ảnh xúc xắc
    total_width = sum(img.width for img in images) + padding * (len(images) - 1)
    max_height = max(img.height for img in images)
    new_image = Image.new('RGBA', (total_width, max_height))

    x_offset = 0
    for img in images:
        new_image.paste(img, (x_offset, 0))
        x_offset += img.width + padding

    # Lưu ảnh ghép vào bộ nhớ tạm
    with BytesIO() as image_binary:
        new_image.save(image_binary, 'PNG')
        image_binary.seek(0)
        
        # Gửi kết quả cuối cùng
        await ctx.send(result_message, file=discord.File(fp=image_binary, filename='dice_combined.png'))
        
    # Gửi kết quả tổng, loại và chẵn/lẻ
    await ctx.send(f'**{result_tai_xiu}** **{result_chan_le}** – **{total}**')

@bot.command()
async def invite(ctx):
    client_id = '1250624872787218522'
    invite_url = f"https://discord.com/oauth2/authorize?client_id={client_id}&scope=bot&permissions=8"
    await ctx.send(f"Thêm bot vào server bằng link sau: {invite_url}")



@bot.command(name='say')
async def say(ctx, *, text: str):
    if ctx.voice_client:
        # Tạo file âm thanh từ văn bản
        tts = gTTS(text, lang='vi')
        tts.save('message.mp3')
    
        # Chuyển đổi file mp3 sang wav vì discord.py chỉ hỗ trợ wav
        sound = AudioSegment.from_mp3('message.mp3')
        sound.export('message.wav', format='wav')

        # Phát âm thanh
        ctx.voice_client.play(discord.FFmpegPCMAudio('message.wav'), after=lambda e: print('done', e))

        # Chờ phát xong rồi xóa file
        while ctx.voice_client.is_playing():
            await asyncio.sleep(1)
        
        # Xóa file sau khi phát xong
        os.remove('message.mp3')
        os.remove('message.wav')
    else:
        await ctx.send("Bot cần phải ở trong kênh thoại để nói!")

# giveaway
def parse_time(time_str: str) -> int:
    """
    Chuyển đổi chuỗi thời gian (ví dụ: 1h30m15s) thành giây.
    """
    time_pattern = re.compile(r'(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?')
    match = time_pattern.fullmatch(time_str.strip())

    if not match:
        raise ValueError("Định dạng thời gian không hợp lệ. Hãy sử dụng định dạng như '1h30m15s'.")

    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0

    return hours * 3600 + minutes * 60 + seconds



@bot.command(name="giveaway", aliases=['ga'])
async def start_giveaway(ctx, time: str = None, winners: int = None, *, prize: str = None):
    """
    Lệnh bắt đầu giveaway.
    Cú pháp: ?giveaway <thời gian (ví dụ: 1h30m)> <số người thắng> <phần thưởng>
    """
    # Kiểm tra tham số đầu vào
    if time is None or winners is None or prize is None:
        await ctx.send("❌ Sai cú pháp! Vui lòng dùng: `?giveaway <thời gian (ví dụ: 1h30m)> <số người thắng> <phần thưởng>`")
        return

    if winners < 1:
        await ctx.send("❌ Số lượng người thắng phải lớn hơn 0!")
        return

    try:
        # Chuyển đổi thời gian thành giây
        time_in_seconds = parse_time(time)
    except ValueError as e:
        await ctx.send(f"❌ {e}")
        return

    # Tạo embed thông báo giveaway
    embed = discord.Embed(
        title="🎉 Giveaway! 🎉",
        description=f"Tham gia giveaway để có cơ hội nhận: **{prize}**\nSố lượng người thắng: {winners}\nNhấn 🎉 để tham gia!",
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Giveaway kết thúc trong {time}!")
    embed.set_author(name=f"Giveaway được tạo bởi {ctx.author.name}", icon_url=ctx.author.avatar.url)

    # Gửi tin nhắn giveaway
    giveaway_message = await ctx.send(embed=embed)
    await giveaway_message.add_reaction("🎉")

    # Đếm ngược thời gian
    while time_in_seconds > 0:
        await asyncio.sleep(5)  # Đợi 5 giây
        time_in_seconds -= 5

        # Cập nhật thời gian còn lại
        hours, remainder = divmod(time_in_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        time_str = f"{hours}h {minutes}m {seconds}s" if hours > 0 else \
                   f"{minutes}m {seconds}s" if minutes > 0 else \
                   f"{seconds}s"
        
        embed.set_footer(text=f"Giveaway kết thúc trong {time_str}!")
        await giveaway_message.edit(embed=embed)

    # Khi thời gian kết thúc, xử lý kết quả giveaway
    try:
        # Lấy lại tin nhắn giveaway
        new_message = await ctx.channel.fetch_message(giveaway_message.id)

        # Lấy danh sách người dùng đã tham gia
        users = [user async for user in new_message.reactions[0].users()]
        users = [user for user in users if user != bot.user]  # Loại bot khỏi danh sách

        # Kiểm tra người tham gia
        if users:
            if len(users) < winners:
                winners = len(users)  # Nếu người tham gia ít hơn số người thắng, giảm số người thắng

            # Chọn người thắng ngẫu nhiên
            winners_list = random.sample(users, winners)
            winners_mentions = ", ".join([winner.mention for winner in winners_list])

            await ctx.send(f"🎉 Chúc mừng {winners_mentions} đã thắng giveaway! Bạn nhận được: **{prize}**")
        else:
            await ctx.send("❌ Không có ai tham gia giveaway. 😢")
    except Exception as e:
        print(f"Lỗi khi xử lý giveaway: {e}")
        await ctx.send("❌ Đã xảy ra lỗi khi kết thúc giveaway.")




@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear_messages(ctx, amount: int = None):
    """
    Lệnh xóa tin nhắn trong kênh hiện tại.
    Cú pháp: !clear <số lượng tin nhắn>
    """
    if amount is None or amount <= 0:
        await ctx.send("❌ Vui lòng nhập số lượng tin nhắn cần xóa (lớn hơn 0).")
        return

    try:
        while amount > 0:
            delete_count = min(amount, 100)  # Tối đa 100 tin nhắn mỗi lần
            deleted = await ctx.channel.purge(limit=delete_count)
            amount -= len(deleted)

            # Tạo khoảng nghỉ 1 giây giữa các lần xóa
            await asyncio.sleep(1)

        confirmation = await ctx.send("✅ Đã xóa thành công tin nhắn trong kênh này.")
        await asyncio.sleep(5)  # Tự động xóa thông báo sau 5 giây
        await confirmation.delete()
    except Exception as e:
        print(f"Lỗi khi xóa tin nhắn: {e}")
        await ctx.send("❌ Đã xảy ra lỗi khi xóa tin nhắn.")



# Thay thế 'YOUR_BOT_TOKEN' bằng token thực tế của bạn
bot.run('')



#invite: https://discord.com/oauth2/authorize?client_id=1250624872787218522&permissions=8&integration_type=0&scope=bot


