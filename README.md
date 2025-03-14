# WordQuery 单词查询插件

这是一个用于查询英语单词的dow插件，可以提供单词的详细解释和发音。

如需使用语音功能需要对 gewechat 源码进行以下修改： 详细教程可参考：[SearchMusic教程的语音配置部分](https://rq4rfacax27.feishu.cn/wiki/L4zFwQmbKiZezlkQ26jckBkcnod?fromScene=spaceOverview)

1. 安装依赖

# 安装处理音频文件的必要依赖
sudo yum install ffmpeg   # FFmpeg用于处理音频、视频和其他多媒体文件
pip3 install pydub        # pydub用于简单、高效地处理音频文件
pip3 install pilk         # pilk用于处理微信语音文件（.silk格式）

2. 修改 gewechat_channel.py 文件

    增加依赖支持，在原有导入语句中添加：

import uuid
import threading
import glob
from voice.audio_convert import mp3_to_silk, split_audio

    添加临时文件清理任务：

def _start_cleanup_task(self):
    """启动定期清理任务"""
    def _do_cleanup():
        while True:
            try:
                self._cleanup_audio_files()
                self._cleanup_video_files()
                self._cleanup_image_files()
                time.sleep(30 * 60)  # 每30分钟执行一次清理
            except Exception as e:
                logger.error(f"[gewechat] 清理任务异常: {e}")
                time.sleep(60)

    cleanup_thread = threading.Thread(target=_do_cleanup, daemon=True)
    cleanup_thread.start()

    添加音频文件清理方法：

def _cleanup_audio_files(self):
    """清理过期的音频文件"""
    try:
        tmp_dir = TmpDir().path()
        current_time = time.time()
        max_age = 3 * 60 * 60  # 音频文件最大保留3小时

        for ext in ['.mp3', '.silk']:
            pattern = os.path.join(tmp_dir, f'*{ext}')
            for fpath in glob.glob(pattern):
                try:
                    if current_time - os.path.getmtime(fpath) > max_age:
                        os.remove(fpath)
                        logger.debug(f"[gewechat] 清理过期音频文件: {fpath}")
                except Exception as e:
                    logger.warning(f"[gewechat] 清理音频文件失败 {fpath}: {e}")
    except Exception as e:
        logger.error(f"[gewechat] 音频文件清理任务异常: {e}")

3. 修改 audio_convert.py 文件

优化音频转换效果，提升音质（将采样率从24000提升至32000）：

def mp3_to_silk(mp3_path: str, silk_path: str) -> int:
    """转换MP3文件为SILK格式，并优化音质"""
    try:
        audio = AudioSegment.from_file(mp3_path)
        audio = audio.set_channels(1)
        audio = audio.set_frame_rate(32000)
        
        pcm_path = os.path.splitext(mp3_path)[0] + '.pcm'
        audio.export(pcm_path, format='s16le', parameters=["-acodec", "pcm_s16le", "-ar", "32000", "-ac", "1"])
        
        try:
            pilk.encode(pcm_path, silk_path, pcm_rate=32000, tencent=True, complexity=2)
            duration = pilk.get_duration(silk_path)
            if duration <= 0:
                raise Exception("Invalid SILK duration")
            return duration
        finally:
            if os.path.exists(pcm_path):
                try:
                    os.remove(pcm_path)
                except Exception as e:
                    logger.warning(f"[audio_convert] 清理PCM文件失败: {e}")
    except Exception as e:
        logger.error(f"[audio_convert] MP3转SILK失败: {e}")
        return 0



## 功能特点

- 通过关键词 `单词 {单词}` 触发查询
- 使用Chat模型获取单词的详细解释，包括音标、词性、释义、例句和变形
- 使用TTS模型朗读单词和例句
- 支持直接发送MP3格式的语音消息

## 安装步骤

1. 将本插件目录放置在dow的plugins目录下
2. 编辑`config.json`文件，填入您的TTS和Chat模型的API密钥和基础URL
3. 确保系统已安装ffmpeg（用于音频处理，如果需要）
4. 重启dow

## 配置说明

在`config.json`中配置您的API密钥和模型参数：

```json
{
    "tts": {
        "base": "https://api.siliconflow.cn/v1",
        "api_key": "your_tts_api_key_here",
        "model": "FunAudioLLM/CosyVoice2-0.5B",
        "voice": "FunAudioLLM/CosyVoice2-0.5B:diana",
        "response_format": "mp3"
    },
    "chat": {
        "base": "https://api.openai.com/v1",
        "api_key": "your_chat_api_key_here",
        "model": "gpt-3.5-turbo",
        "temperature": 0.7
    }
}
```

配置项说明：
- `tts`: TTS模型配置（使用硅基流动API）
  - `base`: API基础URL，硅基流动为"https://api.siliconflow.cn/v1"
  - `api_key`: API密钥
  - `model`: TTS模型名称，如"FunAudioLLM/CosyVoice2-0.5B"
  - `voice`: 语音类型，格式为"模型名:声音名"，如"FunAudioLLM/CosyVoice2-0.5B:diana"
  - `response_format`: 响应格式，通常为"mp3"
- `chat`: Chat模型配置
  - `base`: API基础URL，如OpenAI为"https://api.openai.com/v1"
  - `api_key`: API密钥
  - `model`: Chat模型名称，如"gpt-3.5-turbo"等
  - `temperature`: 温度参数，控制输出的随机性，范围0-2，值越低越精确

您可以为TTS和Chat模型使用不同的API提供商和密钥。

### 硅基流动TTS支持的声音

硅基流动的CosyVoice2-0.5B模型支持以下声音：
- alex: 男声
- anna: 女声
- bella: 女声
- benjamin: 男声
- charles: 男声
- claire: 女声
- david: 男声
- diana: 女声（默认）

## 使用方法

1. 发送 `单词 单词名称` 查询单词解释

例如：`单词 tomorrow`


插件将返回类似以下格式的文本解释：

```
tomorrow [təˈmɒr.əʊ] n.明天;明日;未来;将来;来日;
例句:
I have no problem with you working at home tomorrow.
例句翻译
你明天在家里工作，我没有意见。
变形:tomorrows
```
并返回语音消息朗读单词和例句。

## 依赖项

- requests：用于API请求
- ffmpeg：用于音频格式转换（如果需要）

## 注意事项

- 请确保您的API密钥有足够的额度
- 确保系统已正确安装ffmpeg（如果需要进行音频格式转换）
- 如果遇到问题，请查看dow的日志文件

## 常见问题

1. **问题**: 插件无法发送语音
   **解决方案**: 检查TTS API密钥是否正确，以及网络连接是否正常

2. **问题**: 单词解释不准确或格式错误
   **解决方案**: 调整Chat模型的温度参数，或尝试使用不同的Chat模型

3. **问题**: 语音质量不佳
   **解决方案**: 尝试使用不同的TTS声音或模型



## 鸣谢
- [dify-on-wechat](https://github.com/hanfangyuan4396/dify-on-wechat) - 本项目的基础框架
- [SearchMusic](https://github.com/Lingyuzhou111/SearchMusic) - 项目思路来源
- [Gewechat](https://github.com/Devo919/Gewechat) - 微信机器人框架，个人微信二次开发的免费开源框架 


## 打赏

如果您觉得这个项目对您有帮助，欢迎打赏支持作者继续维护和开发更多功能！

![20250314_125818_133_copy](https://github.com/user-attachments/assets/33df0129-c322-4b14-8c41-9dc78618e220)