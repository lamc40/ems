""" 大模型客户端封装 —— 统一入口，禁止视图层直接写 openai/requests

用法：
    from app01.utils.ai import LLMClient
    answer = LLMClient.chat("你好")

配置来源：ems/settings.py（从 .env 读取 SiliconFlow 免费模型配置）
    AI_API_KEY, AI_BASE_URL, AI_MODEL
"""
from openai import OpenAI
from django.conf import settings


class LLMClient:
    """ 把大模型封装成"会写字的函数"：chat(提示词) -> 文本。

    任务书 T1 要求：
    - 统一封装 chat(prompt) 方法，对外复用
    - API_KEY / BASE_URL / MODEL 从环境变量读（settings → .env）
    - 调用失败返回友好提示，禁止页面崩溃
    """

    _client = None

    @classmethod
    def _get_client(cls):
        """ 懒加载：同一进程只初始化一次客户端。"""
        if cls._client is None:
            cls._client = OpenAI(
                api_key=settings.AI_API_KEY,
                base_url=settings.AI_BASE_URL,   # 换服务只需改 base_url
            )
        return cls._client

    @classmethod
    def chat(cls, prompt, system=None):
        """ 发送提示词，返回模型生成的文字。

        :param prompt: 用户问题/任务（必需）
        :param system: 系统角色设定（可选），用于给模型定"人设"
        :return: 模型回答字符串；失败返回友好错误描述
        """
        if not settings.AI_API_KEY:
            return "⚠️ 请先在 .env 中配置 AI_API_KEY（注册 https://cloud.siliconflow.cn 免费获取）"

        client = cls._get_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = client.chat.completions.create(
                model=settings.AI_MODEL,
                messages=messages,
                temperature=0.7,   # 随机度，越低越稳定、越高越多样
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"⚠️ 大模型调用失败：{e}"

    @classmethod
    def chat_messages(cls, messages):
        """ 多轮对话：直接传完整 messages 数组

        messages 格式：[{"role": "system"|"user"|"assistant", "content": "..."}]
        """
        if not settings.AI_API_KEY:
            return "⚠️ 请先在 .env 中配置 AI_API_KEY"

        try:
            resp = cls._get_client().chat.completions.create(
                model=settings.AI_MODEL,
                messages=messages,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"⚠️ 大模型调用失败：{e}"
