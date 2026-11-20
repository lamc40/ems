""" 提示词模板（三段式：角色 + 任务 + 输出格式）

任务书 T2/T3/T4 都复用这里的模板。
"""

# ===== T2：招聘 JD =====
JD_SYSTEM = "你是一名资深 HR，擅长撰写招聘文案。"


def build_jd_prompt(title):
    """ 为指定岗位构造生成 JD 的提示词。"""
    return (
        f"请为「{title}」岗位撰写一份招聘 JD，"
        f"要求包含三部分：岗位职责、任职要求、薪资范围。"
        f"使用简洁中文，全文约 150 字。"
    )


# ===== T3：制度知识库问答 =====
QA_SYSTEM = "你是一名企业制度助手，只能根据提供的资料回答，资料中没有的内容请回答'不知道'。"


def build_qa_prompt(question, context_items):
    """ 把知识库命中的条目拼入提示词，限定"只根据资料回答"。"""
    context = "\n".join(f"《{k.title}》\n{k.content}" for k in context_items)
    return f"【资料】\n{context}\n\n【问题】\n{question}\n\n请用简洁中文回答。"


# ===== T4：数据点评 =====
REVIEW_SYSTEM = "你是一名 HR 数据分析师，擅长用一句话做简洁客观的点评。"


def build_review_prompt(data_text):
    """ 把结构化薪资/考勤数据转成可读文本后构造提示词。"""
    return f"{data_text}\n请生成一句简短、客观的点评或改进建议（约 30 字）。"


# ===== T5：多轮对话（集成梗识别 + 公告识别） =====
CHAT_SYSTEM = (
    "你是公司 HR 智能助手，回答员工关于考勤、请假、报销、薪资等问题。"
    "同时你有两项超能力："
    "1. 网络梗识别 —— 当用户的话里出现网络流行语、职场梗、二次元梗等，你要自然地指出并幽默解释。"
    "2. 公告解读 —— 当用户问起公司公告、通知，或想知道最新消息时，你要基于提供的公告资料准确回答。"
    "回答要简洁、友好。\n\n"
    "⚠️【多义梗语境判断规则 —— 极其重要】\n"
    "很多网络梗有褒贬两面，必须结合用户的语气和上下文判断真实含义：\n"
    "- 看搭配词：「神了」+ 「这招」= 正面（厉害）；「神了」+ 「有个同事」+ 省略号 = 负面（离谱/抽象）\n"
    "- 看语气符号：感叹号！偏正面感叹；省略号... 偏无语调侃；问号？偏质疑反讽\n"
    "- 看说话主题：夸人做事 → 正面；吐槽同事/老板/加班/改需求 → 大概率负面调侃\n"
    "- 常见多义梗的负面信号：神了/真神了 + 抱怨对象（同事/老板）、牛逼/666 + 吐槽加班、绝了/离谱 + 无奈语气\n"
    "判断步骤：先读完整句，提取用户想表达的核心情绪（是夸赞还是吐槽），再解释梗在这个语境下的特定含义。\n"
    "错误示范：用户说「有个同事真神了...」，你却解释成「这同事很厉害」→ 错！应该理解为「这同事做的事很离谱/抽象/让人看不懂」。"
)


def build_chat_system(matched_memes=None, wiki_text=None, notices_text=None):
    """ 构造多轮对话的 system prompt，自动注入梗知识、wiki权威解释和公告资料

    :param matched_memes: Meme 对象列表（梗知识库匹配结果）
    :param wiki_text: 从 cnmeme.wiki 抓取的权威解释文本
    :param notices_text: 公告文本（公告意图时注入）
    :return: 完整的 system 字符串
    """
    parts = [CHAT_SYSTEM]

    if wiki_text:
        # cnmeme.wiki 的权威解释优先于本地知识库
        parts.append(f"\n\n【cnmeme.wiki 权威梗典 —— 必须引用以下内容回答】\n{wiki_text}")
        parts.append("⚠️ 回答梗相关问题时，必须使用上面 cnmeme.wiki 里的具体信息（如来源视频BV号、用法示例等），不要只给通用解释。")
    elif matched_memes:
        parts.append("\n\n【背景知识 —— 当前对话涉及的梗】")
        for m in matched_memes:
            origin_info = f"（来源：{m.origin}）" if m.origin else ""
            parts.append(f"- {m.name}：{m.explanation}{origin_info}")
        parts.append("请结合上面的知识，在回答中自然地解释这些梗。")
        parts.append("⚠️ 如果某个梗的解释里有「多义词」标注，你必须结合用户的语气、标点（感叹号/省略号/问号）、上下文主题来判断是正面还是负面用法。先读整句判断用户是在夸赞还是吐槽。")

    if notices_text:
        parts.append(f"\n\n【公司公告资料 —— 请以此为准回答用户问题】\n{notices_text}")
        parts.append("请根据上面的公告资料回答用户的问题。如果公告里没有相关内容，请说明。")

    return "\n".join(parts)


# ===== 新增：公告智能识别 =====
NOTICE_SYSTEM = "你是公司公告助手，只能根据提供的公告内容回答。回答要简洁友好，能提炼重点。"


def build_notice_summary_prompt(notices_text):
    """ 一键总结所有公告 —— 提取每条公告的核心信息。"""
    return (
        f"【公司最新公告】\n{notices_text}\n\n"
        f"请用简洁中文总结以上公告的核心要点，"
        f"每条公告用 1-2 句话提炼重点和注意事项，"
        f"如果有置顶公告请优先强调。"
    )


def build_notice_qa_prompt(question, notices_text):
    """ 基于公告内容回答用户问题。"""
    return (
        f"【公司公告资料】\n{notices_text}\n\n"
        f"【问题】\n{question}\n\n"
        f"请根据公告内容回答。如果公告里没有相关信息，请明确说明。"
    )


# ===== 梗识别 =====
MEME_SYSTEM = "你是一位网络梗专家，擅长识别和解释中文网络流行语、职场梗、动漫梗等各种梗文化。回答要轻松幽默、通俗易懂。"


def build_meme_prompt(user_input, matched_memes=None):
    """ 梗识别提示词：先看知识库匹配结果，再让 AI 综合分析

    :param user_input: 用户输入的文本
    :param matched_memes: 知识库中匹配到的 Meme 对象列表（可为空）
    """
    if matched_memes:
        # 有匹配的梗 → 让 AI 结合知识库解释
        knowledge_parts = []
        for m in matched_memes:
            origin_info = f"（来源：{m.origin}）" if m.origin else ""
            knowledge_parts.append(
                f"【{m.name}】\n触发词：{m.keywords}\n解释：{m.explanation}{origin_info}"
            )
        knowledge_text = "\n\n".join(knowledge_parts)

        return (
            f"【用户输入】\n{user_input}\n\n"
            f"【知识库匹配到的梗】\n{knowledge_text}\n\n"
            f"请按以下格式输出：\n"
            f"1. 识别到的梗有哪些（列出名称）\n"
            f"2. 每个梗的含义解释（1-2句话）\n"
            f"3. 这些梗在当前语境下表达了什么情绪或意思\n"
            f"如果输入中没用到任何梗，直接说「这段文字里没有明显的梗」。"
        )
    else:
        # 无匹配 → 让 AI 自己识别
        return (
            f"【用户输入】\n{user_input}\n\n"
            f"请分析这段文字中是否包含网络梗、流行语或特定语境下的表达。\n"
            f"如果有，请列出并解释；如果没有，直接说「这段文字里没有明显的梗」。"
        )


def build_meme_explain_prompt(meme_name):
    """ 单纯询问某个梗的含义（知识库没有，让 AI 自己答）"""
    return (
        f"【梗名称】\n{meme_name}\n\n"
        f"请详细解释这个梗的：\n"
        f"1. 含义\n2. 来源/出处（如果知道）\n3. 使用场景\n"
        f"用简洁幽默的方式回答，约100字。"
    )
