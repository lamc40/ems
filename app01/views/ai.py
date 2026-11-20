""" AI 智能助手视图 —— T2 JD 生成 / T3 知识库问答 / T4 数据点评 / T5 多轮对话

参考代码结构：
- @csrf_exempt（AJAX POST 不带 CSRF token）
- try/except 兜底，返回 {"status": False, "error": "..."}，禁止页面崩溃
- 大模型调用一律走 LLMClient.chat()
- 提示词统一从 utils/prompts.py 引用（三段式：角色 + 任务 + 输出格式）
"""
import json
import re

import requests
from urllib.parse import quote

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q

from app01.models import Knowledge, ChatHistory, UserInfo, Attendance, Salary, Notice, Meme
from app01.utils.ai import LLMClient
from app01.utils.prompts import (
    JD_SYSTEM, build_jd_prompt,
    QA_SYSTEM, build_qa_prompt,
    REVIEW_SYSTEM, build_review_prompt,
    CHAT_SYSTEM, build_chat_system,
    NOTICE_SYSTEM, build_notice_summary_prompt, build_notice_qa_prompt,
    MEME_SYSTEM, build_meme_prompt, build_meme_explain_prompt,
)


# ================================================================
# AI 助手首页（入口）
# ================================================================

def ai_index(request):
    """ AI 助手首页 —— 四个 Tab（JD / 知识库 / 点评 / 对话）"""
    employees = UserInfo.objects.select_related('depart').order_by('id')
    return render(request, 'ai_assistant.html', {'employees': employees})


# ================================================================
# T2 —— 智能生成招聘 JD
# ================================================================

@csrf_exempt
def generate_jd(request):
    """ 模块 A：输入岗位名称，返回招聘 JD 文本。"""
    title = (request.POST.get("title") or "").strip()
    if not title:
        return JsonResponse({"status": False, "error": "岗位名称不能为空"})

    try:
        text = LLMClient.chat(build_jd_prompt(title), system=JD_SYSTEM)
        return JsonResponse({"status": True, "data": text})
    except Exception as e:
        return JsonResponse({"status": False, "error": f"生成失败：{e}"})


# ================================================================
# T3 —— 制度知识库问答（简化版 RAG：SQL 关键词检索 + 提示词注入）
# ================================================================

@csrf_exempt
def knowledge_qa(request):
    """ 模块 B：制度知识库问答。

    流程：用户提问 → SQL 关键词模糊检索 → 命中条目拼入 prompt → 限定"只根据资料回答"。
    资料里没有的内容直接返回"不知道"（不浪费 token）。
    """
    question = (request.POST.get("question") or "").strip()
    if not question:
        return JsonResponse({"status": False, "error": "问题不能为空"})

    # 1) SQL 关键词检索：中文没空格，所以用规则切 + 常见词库
    # 先把标点清掉，再按 2 字符滑窗切（覆盖中文词）
    cleaned = question.replace('？', '').replace('?', '').replace('，', '').replace(',', '').replace('的', '').replace('吗', '')
    keywords = [cleaned[i:i+2] for i in range(len(cleaned)-1) if cleaned[i:i+2].strip()]
    all_keywords = list(set([question] + keywords))

    q = Q()
    for kw in all_keywords:
        q |= Q(title__icontains=kw) | Q(content__icontains=kw)

    items = list(Knowledge.objects.filter(q).distinct()[:5])

    if not items:
        # 没检索到资料：直接兜底，不调用模型
        return JsonResponse({"status": True, "data": "不知道，公司暂无相关制度。"})

    try:
        prompt = build_qa_prompt(question, items)
        text = LLMClient.chat(prompt, system=QA_SYSTEM)
        return JsonResponse({"status": True, "data": text})
    except Exception as e:
        return JsonResponse({"status": False, "error": f"回答失败：{e}"})


# ================================================================
# T4 —— 数据智能点评（结构化数据 → 文本 → 点评）
# ================================================================

def _build_data_text(employee_id: int, month: str) -> str:
    """ 把某员工某月的考勤 + 薪资数据序列化为自然语言文本。"""
    emp = UserInfo.objects.select_related('depart').filter(id=employee_id).first()
    if not emp:
        return ""

    # 考勤
    year, m = month.split('-')
    atts = Attendance.objects.filter(
        employee=emp, date__year=int(year), date__month=int(m),
    ).order_by('date')
    att_parts = []
    for a in atts:
        morning = a.morning_time.strftime('%H:%M') if a.morning_time else '--'
        evening = a.evening_time.strftime('%H:%M') if a.evening_time else '--'
        att_parts.append(f"{a.date} 上班{morning} 下班{evening} 状态{a.status}")
    att_text = f"考勤共 {atts.count()} 天：" + ('；'.join(att_parts) if att_parts else '无记录')

    # 薪资
    sal = Salary.objects.filter(employee=emp, month=month).first()
    sal_text = (
        f"薪资：基本工资 {sal.base_salary}，奖金 {sal.bonus}，扣款 {sal.deduction}，实发 {sal.total}"
        if sal else '薪资：无记录'
    )

    return f"员工 {emp.name}（{emp.depart}）{month} 月数据：{att_text}；{sal_text}"


@csrf_exempt
def employee_review(request):
    """ 模块 C：对某员工某月考勤+薪资数据生成一句点评。"""
    try:
        employee_id = int(request.POST.get("employee", 0))
    except (TypeError, ValueError):
        return JsonResponse({"status": False, "error": "员工参数无效"})

    month = (request.POST.get("month") or "").strip()
    if not month or len(month) != 7 or month[4] != '-':
        return JsonResponse({"status": False, "error": "请选择月份（格式 YYYY-MM）"})

    data_text = _build_data_text(employee_id, month)
    if not data_text:
        return JsonResponse({"status": False, "error": "未找到该员工"})

    try:
        prompt = build_review_prompt(data_text)
        text = LLMClient.chat(prompt, system=REVIEW_SYSTEM)
        return JsonResponse({"status": True, "data": text})
    except Exception as e:
        return JsonResponse({"status": False, "error": f"生成失败：{e}"})


# ================================================================
# T5 —— 多轮对话助手（前端回传历史）
# ================================================================

@csrf_exempt
def chat_stream(request):
    """ 模块 D：带历史的多轮对话（集成梗识别 + 公告识别）

    流程：
    1. 梗识别：用户消息 → 梗库关键词匹配 → 命中的梗注入 system prompt
    2. 公告识别：检测公告意图关键词 → 拉取公告数据 → 注入 system prompt
    AI 就会自然地解释梗、引用公告内容回答。
    """
    question = (request.POST.get("question") or "").strip()
    if not question:
        return JsonResponse({"status": False, "error": "问题不能为空"})

    try:
        history = json.loads(request.POST.get("history", "[]"))
    except (json.JSONDecodeError, TypeError):
        history = []

    # ===== 1) 梗识别：本地库匹配 + cnmeme.wiki 权威解释 =====
    matched_memes = _match_memes_in_text(question)
    for h in history[-6:]:
        if h.get("role") == "user":
            matched_memes += _match_memes_in_text(h.get("content", ""))
    seen = set()
    matched_memes = [m for m in matched_memes if m.id not in seen and not seen.add(m.id)]

    # 梗解释优先用 wiki/热点缓存，本地匹配的梗作为 backup
    wiki_text_blob = None
    wiki_sources = []  # 记录每个梗的来源（wiki 还是 local）
    if matched_memes:
        wiki_parts = []
        for meme in matched_memes[:5]:
            cached = _fetch_and_cache_meme(meme.name)
            if cached:
                wiki_parts.append(_format_meme_for_prompt(cached))
                wiki_sources.append(f"{cached['name']}({cached['source']})")
                # 至少拿到一个就停（避免限流）
                if cached["source"] == "wiki":
                    break  # 刚从 wiki 抓到一个，不继续请求了
        wiki_text_blob = "\n\n".join(wiki_parts) if wiki_parts else None

    # ===== 2) 公告识别：意图检测 + 拉数据 =====
    notices_text = None
    matched_notices_titles = []
    notice_keywords = [
        "公告", "通知", "通告", "发布", "最新", "总结", "今日", "今天",
        "有什么消息", "有哪些公告", "有什么通知", "最新消息", "公告栏",
    ]
    has_notice_intent = any(kw in question for kw in notice_keywords)

    if has_notice_intent:
        # 先尝试关键词检索匹配公告
        cleaned = question.replace('？', '').replace('?', '').replace('，', '').replace(',', '').replace('的', '')
        keywords = [cleaned[i:i+2] for i in range(len(cleaned)-1) if cleaned[i:i+2].strip()]
        all_kws = list(set([question] + keywords))

        q = Q()
        for kw in all_kws:
            q |= Q(title__icontains=kw) | Q(content__icontains=kw)

        matched_notices = list(
            Notice.objects.filter(q).select_related('author')
            .order_by('-is_top', '-created_at')[:5]
        )

        if matched_notices:
            # 检索到匹配的公告
            notices_text = _build_notices_text(matched_notices)
            matched_notices_titles = [n.title for n in matched_notices]
        else:
            # 没搜到，把最新公告都给 AI 让它说
            latest = list(
                Notice.objects.select_related('author')
                .order_by('-is_top', '-created_at')[:5]
            )
            if latest:
                notices_text = _build_notices_text(latest)
                matched_notices_titles = [n.title for n in latest]

    # ===== 3) 构造 system prompt（同时注入梗 + cnmeme.wiki 权威解释 + 公告）=====
    system_text = build_chat_system(
        matched_memes=matched_memes[:5],
        wiki_text=wiki_text_blob,
        notices_text=notices_text,
    )

    messages = [{"role": "system", "content": system_text}]
    messages += history
    messages.append({"role": "user", "content": question})

    try:
        answer = LLMClient.chat_messages(messages)
        return JsonResponse({
            "status": True,
            "data": answer,
            "matched_memes": [m.name for m in matched_memes[:5]],
            "matched_notices": matched_notices_titles,
        })
    except Exception as e:
        return JsonResponse({"status": False, "error": f"对话失败：{e}"})


# ================================================================
# 新增 —— 公告智能识别（总结 + 问答双模式）
# ================================================================

def _build_notices_text(notices):
    """ 把 Notice 列表序列化成给 AI 看的文本。"""
    parts = []
    for n in notices:
        top_tag = "[置顶] " if n.is_top else ""
        parts.append(
            f"{top_tag}《{n.title}》\n"
            f"发布时间：{n.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            f"发布人：{n.author.username if n.author else '系统'}\n"
            f"内容：{n.content}"
        )
    return "\n\n".join(parts)


@csrf_exempt
def notice_qa(request):
    """ 模块 E：公告智能识别。

    双模式：
    - 不传 question → 一键总结全部公告（按置顶优先 + 时间倒序，最多 10 条）
    - 传 question → 先检索匹配公告，再让 AI 基于公告内容回答
    """
    question = (request.POST.get("question") or "").strip()

    # 取公告：置顶优先 + 时间倒序，最多 10 条（控制 token）
    all_notices = Notice.objects.select_related('author').order_by('-is_top', '-created_at')[:10]

    if question:
        # === 问答模式 ===
        # 先用 SQL 关键词检索缩小范围
        cleaned = question.replace('？', '').replace('?', '').replace('，', '').replace(',', '').replace('的', '')
        keywords = [cleaned[i:i+2] for i in range(len(cleaned)-1) if cleaned[i:i+2].strip()]
        all_keywords = list(set([question] + keywords))

        q = Q()
        for kw in all_keywords:
            q |= Q(title__icontains=kw) | Q(content__icontains=kw)

        matched = list(Notice.objects.filter(q).select_related('author').order_by('-is_top', '-created_at')[:5])

        if not matched:
            # 没搜到，把全部公告给 AI（让它说有没有相关内容）
            matched = list(all_notices)

        if not matched:
            return JsonResponse({"status": True, "data": "公司暂无任何公告。"})

        notices_text = _build_notices_text(matched)
        try:
            prompt = build_notice_qa_prompt(question, notices_text)
            text = LLMClient.chat(prompt, system=NOTICE_SYSTEM)
            return JsonResponse({"status": True, "data": text})
        except Exception as e:
            return JsonResponse({"status": False, "error": f"回答失败：{e}"})

    else:
        # === 总结模式 ===
        if not all_notices:
            return JsonResponse({"status": True, "data": "公司暂无任何公告。"})

        notices_text = _build_notices_text(list(all_notices))
        try:
            prompt = build_notice_summary_prompt(notices_text)
            text = LLMClient.chat(prompt, system=NOTICE_SYSTEM)
            return JsonResponse({"status": True, "data": text})
        except Exception as e:
            return JsonResponse({"status": False, "error": f"总结失败：{e}"})


# ================================================================
# 梗识别 —— 识别输入文本中的网络梗并解释
# ================================================================

def _match_memes_in_text(text):
    """ 在梗知识库中查找与输入文本匹配的梗

    返回匹配到的 Meme 对象列表。匹配规则：
    - 梗的名称包含在文本中
    - 或梗的某个关键词包含在文本中
    """
    active_memes = Meme.objects.filter(is_active=True)
    matched = []
    text_lower = text.lower()

    for meme in active_memes:
        # 先检查梗名称本身
        if meme.name and meme.name.lower() in text_lower:
            matched.append(meme)
            continue
        # 再检查每个关键词
        for kw in meme.get_keyword_list():
            if kw.lower() in text_lower:
                matched.append(meme)
                break

    return matched


def _fetch_meme_from_wiki(keyword):
    """ 从 cnmeme.wiki 抓取梗的原始数据（返回 dict，方便后续存库）

    :return: dict{title, content, origin, explanation} 或 None
    """
    try:
        url = "https://cnmeme.wiki/entry/" + quote(keyword)
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=15,
        )
        if resp.status_code != 200:
            return None

        # 提取标题 H1
        title_m = re.search(r"<h1[^>]*>(.*?)</h1>", resp.text, re.DOTALL)
        title = re.sub(r"<[^>]+>", "", title_m.group(1)).strip() if title_m else keyword

        # 没找到条目
        if "page not found" in resp.text.lower() and title.lower() == keyword.lower():
            return None

        # 提取正文 article
        content_m = re.search(r"<article[^>]*>(.*?)</article>", resp.text, re.DOTALL)
        if not content_m:
            return None

        content = re.sub(r"<[^>]+>", " ", content_m.group(1))
        content = re.sub(r"\s+", " ", content).strip()

        # 提取来源视频 BV 号或来源文字
        origin = ""
        bv_m = re.search(r"(BV[0-9A-Za-z]+)", content)
        if bv_m:
            origin = bv_m.group(1)
        else:
            src_m = re.search(r"来源\s*([^用法]{2,50})", content)
            if src_m:
                origin = src_m.group(1).strip()

        # 正文里去掉模板残留
        explanation = re.sub(r"词条地址[^来源]*来源", "来源", content)
        explanation = explanation[:800]

        return {
            "title": title,
            "content": content,
            "origin": origin,
            "explanation": explanation,
        }
    except Exception:
        return None


# 内存缓存：keyword → 抓回来的完整 dict（避免重复查 DB + 请求 wiki）
_wiki_cache = {}


def _fetch_and_cache_meme(keyword):
    """ 热点缓存模式：本地 Meme 表优先 → wiki 抓取 → 自动回写本地

    返回值：
    - 成功：dict{source, name, explanation, origin, keywords}
        source='local' 表示来自本地 Meme 表，source='wiki' 表示刚从 wiki 抓的
    - 失败：None
    """
    # 0) 内存缓存最快
    if keyword in _wiki_cache:
        return _wiki_cache[keyword]

    # 1) 查本地 Meme 表
    local = Meme.objects.filter(name=keyword, is_active=True).first()
    if local:
        result = {
            "source": "local",
            "name": local.name,
            "explanation": local.explanation,
            "origin": local.origin,
            "keywords": local.keywords,
        }
        _wiki_cache[keyword] = result
        return result

    # 2) 去 cnmeme.wiki 抓
    wiki = _fetch_meme_from_wiki(keyword)
    if wiki:
        # 2a) 存进本地 Meme 表（热点缓存！以后就不用再抓了）
        try:
            meme = Meme.objects.create(
                name=wiki["title"],
                keywords=keyword,  # 触发词就存搜索词本身
                explanation=wiki["explanation"],
                origin=wiki["origin"],
                category="internet",
                is_active=True,
            )
        except Exception:
            meme = None  # 重复创建或其他错误，忽略

        result = {
            "source": "wiki",
            "name": wiki["title"],
            "explanation": wiki["explanation"],
            "origin": wiki["origin"],
            "keywords": keyword,
        }
        _wiki_cache[keyword] = result
        return result

    # 3) 都没找到
    _wiki_cache[keyword] = None
    return None


def _format_meme_for_prompt(meme_dict):
    """ 把 _fetch_and_cache_meme 返回的 dict 拼成 prompt 用的文本 """
    if not meme_dict:
        return None
    origin_info = f"（来源：{meme_dict['origin']}）" if meme_dict.get("origin") else ""
    source_tag = "cnmeme.wiki" if meme_dict["source"] == "wiki" else "本地知识库"
    return f"【{source_tag}】{meme_dict['name']}\n{meme_dict['explanation']}{origin_info}"


@csrf_exempt
def meme_recognize(request):
    """ 模块 F：梗识别

    两种模式：
    - mode=recognize（默认）：分析用户输入文本，识别其中的梗
    - mode=explain：查询某个梗的含义（无论知识库有没有都让 AI 解释）

    识别模式流程：
    1. 先在梗知识库中做关键词匹配（快速命中）
    2. 把命中的梗 + 用户输入一起给大模型，让它综合分析
    3. 知识库没有的梗也能识别（大模型自己的知识）
    """
    user_input = (request.POST.get("text") or "").strip()
    mode = (request.POST.get("mode") or "recognize").strip()

    if not user_input:
        return JsonResponse({"status": False, "error": "请输入要识别的文本或梗名称"})

    try:
        if mode == "explain":
            # === 解释单个梗 ===
            # 先查知识库有没有
            matched = _match_memes_in_text(user_input)
            if matched:
                # 知识库有 → 直接返回解释（不浪费 token）
                meme = matched[0]
                origin_info = f"（来源：{meme.origin}）" if meme.origin else ""
                text = f"🗣️ {meme.name}\n\n{meme.explanation}{origin_info}"
            else:
                # 知识库没有 → 让大模型解释
                prompt = build_meme_explain_prompt(user_input)
                text = LLMClient.chat(prompt, system=MEME_SYSTEM)
            return JsonResponse({"status": True, "data": text})

        else:
            # === 识别文本中的梗 ===
            matched = _match_memes_in_text(user_input)
            prompt = build_meme_prompt(user_input, matched_memes=matched[:5])  # 最多5个匹配
            text = LLMClient.chat(prompt, system=MEME_SYSTEM)
            return JsonResponse({
                "status": True,
                "data": text,
                "matched_count": len(matched),
                "matched_memes": [m.name for m in matched],
            })

    except Exception as e:
        return JsonResponse({"status": False, "error": f"识别失败：{e}"})


# ================================================================
# 梗知识库管理（增删改查，给管理员用）
# ================================================================

def meme_list(request):
    """ 梗库列表 —— 后台管理用"""
    memes = Meme.objects.all().order_by('-created_at')
    return render(request, 'meme_list.html', {'memes': memes})


@csrf_exempt
def meme_add(request):
    """ 新增梗到知识库"""
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        keywords = (request.POST.get('keywords') or '').strip()
        explanation = (request.POST.get('explanation') or '').strip()
        origin = (request.POST.get('origin') or '').strip()
        category = request.POST.get('category', 'internet')

        if not name or not keywords or not explanation:
            return JsonResponse({"status": False, "error": "梗名称、关键词、解释都不能为空"})

        meme = Meme.objects.create(
            name=name, keywords=keywords, explanation=explanation,
            origin=origin, category=category, is_active=True,
        )
        return JsonResponse({"status": True, "data": f"已添加「{meme.name}」"})

    # GET → 返回空表单模板（简单起见直接用 JsonResponse）
    return JsonResponse({"status": False, "error": "请用 POST 请求提交"})


@csrf_exempt
def meme_toggle(request):
    """ 切换梗的启用状态"""
    try:
        meme_id = int(request.POST.get('id', 0))
        meme = Meme.objects.get(id=meme_id)
        meme.is_active = not meme.is_active
        meme.save()
        status = "启用" if meme.is_active else "停用"
        return JsonResponse({"status": True, "data": f"已{status}「{meme.name}」"})
    except (Meme.DoesNotExist, ValueError):
        return JsonResponse({"status": False, "error": "梗不存在"})


@csrf_exempt
def meme_delete(request):
    """ 删除一个梗"""
    try:
        meme_id = int(request.POST.get('id', 0))
        meme = Meme.objects.get(id=meme_id)
        name = meme.name
        meme.delete()
        return JsonResponse({"status": True, "data": f"已删除「{name}」"})
    except (Meme.DoesNotExist, ValueError):
        return JsonResponse({"status": False, "error": "梗不存在"})
