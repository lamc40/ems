""" 公告管理视图：列表/发布/编辑/删除/切换置顶

auto_now_add 自动写入发布时间，is_top 控制置顶（ORDER BY -is_top, -created_at）。
"""
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q

from app01.models import Notice
from app01.utils.pagination import Pagination

User = get_user_model()


def notice_list(request):
    """ 公告列表：支持按标题搜索 + 分页 + 置顶优先排序 """
    search = request.GET.get('search', '').strip()
    queryset = Notice.objects.select_related('author').all()
    if search:
        queryset = queryset.filter(Q(title__contains=search) | Q(content__contains=search))

    page_object = Pagination(request, queryset, page_size=10)
    return render(request, 'notice_list.html', {
        'notice_list': page_object.page_queryset,
        'page_str': page_object.html(),
        'search': search,
    })


def notice_add(request):
    """ 发布公告 """
    if request.method == "POST":
        Notice.objects.create(
            title=request.POST.get('title'),
            content=request.POST.get('content'),
            author=request.user,
            is_top=request.POST.get('is_top') == 'on',
        )
        return redirect('/notice/list/')

    return render(request, 'notice_add.html')


def notice_edit(request, nid):
    """ 编辑公告 """
    obj = get_object_or_404(Notice, id=nid)
    if request.method == "POST":
        obj.title = request.POST.get('title')
        obj.content = request.POST.get('content')
        obj.is_top = request.POST.get('is_top') == 'on'
        obj.save()
        return redirect('/notice/list/')

    return render(request, 'notice_add.html', {'notice': obj, 'title': '编辑公告'})


def notice_delete(request, nid):
    """ 删除公告 """
    Notice.objects.filter(id=nid).delete()
    return redirect('/notice/list/')


def notice_toggle_top(request, nid):
    """ 切换置顶状态（快捷按钮，AJAX 友好） """
    obj = get_object_or_404(Notice, id=nid)
    obj.is_top = not obj.is_top
    obj.save()
    return redirect('/notice/list/')
