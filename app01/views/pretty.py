""" 靓号管理视图：列表（搜索+分页）/ 新增 / 编辑 / 删除 """
from django.db import connection
from django.shortcuts import render, redirect, get_object_or_404

from app01.models import PrettyNum
from app01.utils.form import PrettyModelForm, PrettyEditModelForm
from app01.utils.pagination import Pagination


def pretty_list(request):
    """ 靓号列表（含号码模糊搜索 + 分页，分页时自动保留搜索条件） """
    search = request.GET.get('search', '')          # 获取搜索框提交的关键字，默认空字符串
    queryset = PrettyNum.objects.all().order_by('id')  # 全部靓号，按ID升序
    if search:
        queryset = queryset.filter(mobile__contains=search)
    page_object = Pagination(request, queryset)     # 分页处理（默认每页10条）
    return render(request, 'pretty_list.html', {
        'pretty_list': page_object.page_queryset,   # 当前页的数据
        'search': search,                           # 回传关键字，用于搜索框回显
        'page_str': page_object.html(),             # 分页条HTML
    })


def pretty_add(request):
    """ 新建靓号（ModelForm） """
    if request.method == "POST":
        form = PrettyModelForm(data=request.POST)   # 提交的数据交给ModelForm校验
        if form.is_valid():                          # 格式+唯一性校验全部通过
            form.save()                              # ModelForm直接写入数据库
            return redirect('/pretty/list/')
        # 校验失败时带着错误信息重新渲染表单（errors显示在字段下方）
    form = PrettyModelForm()                         # GET请求：空表单
    return render(request, 'pretty_add.html', {'form': form})


def pretty_edit(request, nid):
    """ 编辑靓号（ModelForm，instance指定要修改的行） """
    row = get_object_or_404(PrettyNum, id=nid)       # 根据URL中的id取记录，不存在则404
    if request.method == "POST":
        # instance=row 表示更新已有记录而不是新建；data为提交的修改内容
        form = PrettyEditModelForm(data=request.POST, instance=row)
        if form.is_valid():
            form.save()                              # 保存修改
            return redirect('/pretty/list/')
    form = PrettyEditModelForm(instance=row)          # GET请求：用已有数据填充表单
    return render(request, 'pretty_edit.html', {'form': form})


def pretty_delete(request, nid):
    """ 删除靓号并重新排序ID，使ID保持连续 """
    PrettyNum.objects.filter(id=nid).delete()        # 删除指定行
    # 重新排序剩余靓号ID，使其连续（如删除id=1后，2,3,4 -> 1,2,3）
    queryset = list(PrettyNum.objects.all().order_by('id'))
    with connection.cursor() as cursor:
        for index, row in enumerate(queryset, start=1):
            if row.id != index:
                # ORM不能直接改主键，用原生SQL逐行更新ID
                cursor.execute(
                    "UPDATE app01_prettynum SET id=%s WHERE id=%s",
                    [index, row.id],
                )
        # 重置自增计数器，使下次新建的ID从当前最大值+1开始
        cursor.execute(
            "ALTER TABLE app01_prettynum AUTO_INCREMENT = %s",
            [len(queryset) + 1],
        )
    return redirect('/pretty/list/')
