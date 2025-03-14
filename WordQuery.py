#!/usr/bin/env python3
# encoding:utf-8

import json
import requests
import os
import time
import random
import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from common.tmp_dir import TmpDir
from plugins import *

@plugins.register(
    name="WordQuery",
    desire_priority=10,
    desc="输入关键词'单词 单词名称'即可获取单词的详细解释和发音",
    version="1.0",
    author="AI Assistant",
)
class WordQuery(Plugin):
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        self.config_file = os.path.join(os.path.dirname(__file__), "config.json")
        self.config = self.load_config()
        logger.info("[WordQuery] 插件已初始化")

    def load_config(self):
        """
        加载配置文件
        :return: 配置字典
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    logger.info(f"[WordQuery] 成功加载配置文件")
                    return config
            else:
                # 创建默认配置
                default_config = {
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
                with open(self.config_file, "w", encoding="utf-8") as f:
                    json.dump(default_config, f, indent=4)
                logger.info(f"[WordQuery] 已创建默认配置文件")
                return default_config
        except Exception as e:
            logger.error(f"[WordQuery] 加载配置文件失败: {e}")
            return {
                "tts": {
                    "base": "https://api.siliconflow.cn/v1", 
                    "api_key": "",
                    "model": "FunAudioLLM/CosyVoice2-0.5B",
                    "voice": "FunAudioLLM/CosyVoice2-0.5B:diana",
                    "response_format": "mp3"
                },
                "chat": {
                    "base": "https://api.openai.com/v1", 
                    "api_key": "",
                    "model": "gpt-3.5-turbo",
                    "temperature": 0.7
                }
            }

    def query_word(self, word):
        """
        使用Chat模型查询单词信息
        :param word: 要查询的单词
        :return: 单词解释文本
        """
        try:
            if not self.config["chat"]["api_key"] or self.config["chat"]["api_key"] == "your_chat_api_key_here":
                return f"请先在config.json中配置正确的Chat API密钥"

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config['chat']['api_key']}"
            }

            # 从配置中获取模型和温度
            model = self.config["chat"].get("model", "gpt-3.5-turbo")
            temperature = self.config["chat"].get("temperature", 0.7)

            data = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个英语词典助手。请严格按照以下示例格式提供单词解释：\n\nquit [kwɪt] v.停止；放弃；离开；辞职;\n例句:\nShe decided to quit her job and travel the world.\n例句翻译\n她决定辞去工作，去环游世界。\n变形:quits, quitting, quit\n记忆技巧:将quit与中文'退出'联系起来记忆，两者发音和含义相近，都表示离开或放弃。"
                    },
                    {
                        "role": "user",
                        "content": f"请解释单词 '{word}'，严格按照示例格式回复，包括单词解释、例句、例句翻译、变形和记忆技巧。记忆技巧应该简短实用，可以包括词根分析、谐音联想、图像记忆法等，让人更容易记住该单词。"
                    }
                ],
                "temperature": temperature
            }

            # 添加重试机制
            for retry in range(3):  # 最多重试3次
                try:
                    response = requests.post(
                        f"{self.config['chat']['base']}/chat/completions",
                        headers=headers,
                        json=data,
                        timeout=30
                    )
                    response.raise_for_status()  # 检查响应状态
                    break
                except requests.RequestException as e:
                    if retry == 2:  # 最后一次重试
                        logger.error(f"[WordQuery] 查询单词API请求失败，重试次数已用完: {e}")
                        return f"查询单词 '{word}' 失败，API请求错误: {str(e)}"
                    logger.warning(f"[WordQuery] 查询单词API请求重试 {retry + 1}/3: {e}")
                    time.sleep(1)  # 等待1秒后重试

            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"].strip()
                else:
                    return f"查询单词 '{word}' 失败，API返回结果异常"
            else:
                logger.error(f"[WordQuery] Chat API请求失败: {response.status_code} {response.text}")
                return f"查询单词 '{word}' 失败，API请求错误: {response.status_code}"

        except Exception as e:
            logger.error(f"[WordQuery] 查询单词时出错: {e}")
            return f"查询单词 '{word}' 时发生错误: {str(e)}"

    def text_to_speech(self, text, word):
        """
        使用TTS模型将文本转换为语音
        :param text: 要转换的文本
        :param word: 单词名称（用于文件名）
        :return: 语音文件路径或None（如果转换失败）
        """
        try:
            if not self.config["tts"]["api_key"] or self.config["tts"]["api_key"] == "your_tts_api_key_here":
                logger.error("[WordQuery] 未配置TTS API密钥")
                return None

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config['tts']['api_key']}"
            }

            # 从配置中获取模型和声音
            model = self.config["tts"].get("model", "FunAudioLLM/CosyVoice2-0.5B")
            voice = self.config["tts"].get("voice", "FunAudioLLM/CosyVoice2-0.5B:diana")
            response_format = self.config["tts"].get("response_format", "mp3")
            
            # 根据硅基流动API格式构建请求
            data = {
                "model": model,
                "input": text,
                "voice": voice,
                "response_format": response_format
            }
            
            # 记录请求参数，便于调试
            logger.debug(f"[WordQuery] TTS请求参数: {json.dumps(data)}")

            # 添加重试机制
            for retry in range(3):  # 最多重试3次
                try:
                    response = requests.post(
                        f"{self.config['tts']['base']}/audio/speech",
                        headers=headers,
                        json=data,
                        timeout=30
                    )
                    response.raise_for_status()  # 检查响应状态
                    break
                except requests.RequestException as e:
                    if retry == 2:  # 最后一次重试
                        logger.error(f"[WordQuery] TTS API请求失败，重试次数已用完: {e}")
                        return None
                    logger.warning(f"[WordQuery] TTS API请求重试 {retry + 1}/3: {e}")
                    time.sleep(1)  # 等待1秒后重试

            if response.status_code == 200:
                # 使用TmpDir().path()获取正确的临时目录
                tmp_dir = TmpDir().path()
                
                # 生成唯一的文件名
                timestamp = int(time.time())
                random_str = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=6))
                mp3_path = os.path.join(tmp_dir, f"word_{word}_{timestamp}_{random_str}.mp3")
                
                # 保存MP3文件
                with open(mp3_path, "wb") as f:
                    f.write(response.content)
                
                # 验证文件大小
                if os.path.getsize(mp3_path) == 0:
                    logger.error("[WordQuery] 下载的文件大小为0")
                    os.remove(mp3_path)  # 删除空文件
                    return None
                
                logger.info(f"[WordQuery] 语音生成完成: {mp3_path}, 大小: {os.path.getsize(mp3_path)/1024:.2f}KB")
                return mp3_path
                
            else:
                logger.error(f"[WordQuery] TTS API请求失败: {response.status_code} {response.text}")
                return None

        except Exception as e:
            logger.error(f"[WordQuery] 文本转语音时出错: {e}")
            # 如果文件已创建，清理它
            if 'mp3_path' in locals() and os.path.exists(mp3_path):
                try:
                    os.remove(mp3_path)
                except Exception as clean_error:
                    logger.error(f"[WordQuery] 清理失败的语音文件时出错: {clean_error}")
            return None

    def extract_pronunciation_example(self, word_info):
        """
        从单词信息中提取发音和例句
        :param word_info: 单词信息文本
        :return: 用于TTS的文本
        """
        try:
            # 提取单词本身（带音标）
            word_line = word_info.split('\n')[0].strip() if word_info else ""
            word = word_line.split()[0] if word_line else ""  # 获取纯单词
            
            # 尝试提取例句
            example = ""
            if "例句:" in word_info:
                lines = word_info.split("\n")
                for i, line in enumerate(lines):
                    if line.strip() == "例句:":
                        if i + 1 < len(lines):
                            example_line = lines[i + 1].strip()
                            # 规范化例句标点
                            example_line = example_line.rstrip('.!?')  # 去除原有结尾标点
                            example = example_line + '.'  # 统一添加句号
                            break
            
            # 组合TTS文本
            tts_text = f"{word}."  # 单词后固定加句号
            if example:
                tts_text += " " + example  # 添加规范化后的例句
                
            logger.debug(f"[WordQuery] 生成的TTS文本: {tts_text}")  # 添加调试日志
            return tts_text
            
        except Exception as e:
            logger.error(f"[WordQuery] 提取发音和例句时出错: {e}")
            return f"{word_info.split()[0]}." if word_info else ""  # 保证返回带句号的单词

    def send_voice_later(self, word, receiver):
        """
        延迟发送语音的函数（在文本回复之后）
        :param word: 单词
        :param receiver: 接收者
        """
        try:
            # 等待1秒，确保文本消息已经发送
            time.sleep(1)
            
            # 查询单词信息
            word_info = self.query_word(word)
            
            # 提取用于TTS的文本
            tts_text = self.extract_pronunciation_example(word_info)
            
            # 生成语音文件
            voice_path = self.text_to_speech(tts_text, word)
            
            if voice_path:
                logger.info(f"[WordQuery] 延迟发送语音: {voice_path}")
                
                # 使用正确的方式发送语音消息
                from channel.channel_factory import create_channel
                from bridge.reply import Reply, ReplyType
                from bridge.context import Context, ContextType
                
                # 创建一个回复对象
                reply = Reply()
                reply.type = ReplyType.VOICE
                reply.content = voice_path
                
                # 创建一个上下文对象
                context = Context()
                context.type = ContextType.TEXT
                context.content = f"单词听 {word}"  # 为日志记录提供内容
                context.kwargs = {"receiver": receiver, "session_id": receiver}
                
                # 获取channel并发送
                channel = create_channel("gewechat")
                channel.send(reply, context)
                
                logger.info(f"[WordQuery] 成功延迟发送语音给 {receiver}")
            else:
                logger.warning("[WordQuery] 延迟发送语音失败，无法生成语音文件")
        except Exception as e:
            logger.error(f"[WordQuery] 延迟发送语音出错: {e}")

    def on_handle_context(self, e_context: EventContext):
        """
        处理上下文事件
        :param e_context: 事件上下文
        """
        logger.info(f"[WordQuery] on_handle_context 被调用，处理内容: {e_context['context'].content}")
        
        if e_context["context"].type != ContextType.TEXT:
            return
            
        content = e_context["context"].content.strip()
        logger.info(f"[WordQuery] 正在处理内容: {content}")
        
        # 处理单词查询命令
        if content.startswith("单词 "):
            logger.info(f"[WordQuery] 处理单词查询: {content}")
            
            # 创建回复对象
            reply = Reply()
            reply.type = ReplyType.TEXT
            
            word = content[3:].strip()
            if not word:
                reply.content = "请输入要查询的单词"
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK
                return
                
            # 查询单词信息
            word_info = self.query_word(word)
            logger.info(f"[WordQuery] 查询结果: {word_info}")
            
            # 只发送文本解释
            reply.content = word_info
            e_context.action = EventAction.BREAK_PASS
            e_context["reply"] = reply
            logger.info(f"[WordQuery] 设置回复: {reply.content[:30]}... 和EventAction: {e_context.action}")
            
            # 获取接收者ID
            receiver = e_context["context"].kwargs.get("receiver", "")
            if receiver:
                # 创建后台线程发送语音
                import threading
                voice_thread = threading.Thread(target=self.send_voice_later, args=(word, receiver))
                voice_thread.daemon = True
                voice_thread.start()
                logger.info(f"[WordQuery] 已创建后台线程发送语音给 {receiver}")
            
            return True
            
        # 处理单词发音命令
        elif content.startswith("单词听 ") or content.startswith("听单词 "):
            if content.startswith("单词听 "):
                word = content[4:].strip()
            else:
                word = content[4:].strip()
                
            logger.info(f"[WordQuery] 处理单词发音: {content}")
            
            if not word:
                reply = Reply()
                reply.type = ReplyType.TEXT
                reply.content = "请输入要发音的单词"
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK
                return
            
            # 查询单词信息
            word_info = self.query_word(word)
            logger.info(f"[WordQuery] 查询结果: {word_info}")
            
            # 提取用于TTS的文本
            tts_text = self.extract_pronunciation_example(word_info)
            logger.info(f"[WordQuery] TTS文本: {tts_text}")
            
            # 生成语音文件
            voice_path = self.text_to_speech(tts_text, word)
            
            if voice_path:
                logger.info(f"[WordQuery] 生成语音文件: {voice_path}")
                
                # 发送语音消息
                reply = Reply()
                reply.type = ReplyType.VOICE
                reply.content = voice_path
                e_context["reply"] = reply
                
                # 阻止请求传递给其他插件
                e_context.action = EventAction.BREAK_PASS
                logger.info(f"[WordQuery] 设置语音回复和EventAction: {e_context.action}")
                return True
            else:
                logger.warning("[WordQuery] 语音生成失败")
                
                reply = Reply()
                reply.type = ReplyType.TEXT
                reply.content = f"生成\"{word}\"的语音失败，请稍后重试"
                e_context["reply"] = reply
                
                # 阻止请求传递给其他插件
                e_context.action = EventAction.BREAK_PASS
                logger.info(f"[WordQuery] 设置错误回复和EventAction: {e_context.action}")
                return True

    def get_help_text(self, **kwargs):
        """
        获取插件帮助文本
        :return: 帮助文本
        """
        help_text = "📚 单词查询插件 📚\n\n"
        help_text += "使用方法：\n"
        help_text += "- 发送 '单词 单词名称' 查询单词解释\n"
        help_text += "- 发送 '单词听 单词名称' 或 '听单词 单词名称' 获取单词发音\n"
        help_text += "例如：单词 tomorrow、单词听 tomorrow\n\n"
        help_text += "注意：请先在config.json中配置正确的API密钥"
        return help_text 