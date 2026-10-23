""" 视图层：每个函数对应一个URL，负责取数据/处理表单/返回页面 """
from django.db import connection
from django.shortcuts import render, redirect, get_object_or_404

from app01.forms import UserModelForm, PrettyModelForm, PrettyEditModelForm
from app01.models import Department, UserInfo, PrettyNum
from app01.utils.pagination import Pagination


# ============ 部门管理 ============

def depart_list(request):
    """ 部门列表：分页查询部门并渲染到模板 """
    queryset = Department.objects.all().order_by('id')   # 按ID排序，保证分页数据稳定
    page_object = Pagination(request, queryset)          # 分页处理（默认每页10条）
    return render(request, 'depart_list.html', {
        'depart_list': page_object.page_queryset,        # 当前页的数据
        'page_str': page_object.html(),                  # 分页条HTML
    })


def depart_add(request):
    """ 新增部门：GET显示空表单，POST保存后跳回列表 """
    if request.method == "POST":
        title = request.POST.get('title')   # 取表单提交的标题
        Department.objects.create(title=title)
        return redirect('/depart/list/')
    return render(request, 'depart_add.html')


def depart_add2(request):
    """ 新增部门（版本2）：逻辑同上，仅模板不同 """
    if request.method == "POST":
        title = request.POST.get('title')
        Department.objects.create(title=title)
        return redirect('/depart/list/')
    return render(request, 'depart_add2.html')


def depart_edit(request, nid):
    """ 编辑部门：nid来自URL，回显原数据后保存修改 """
    depart = get_object_or_404(Department, id=nid)   # 记录不存在返回404
    if request.method == "POST":
        title = request.POST.get('title')
        depart.title = title
        depart.save()                                # 已有对象save即UPDATE
        return redirect('/depart/list/')
    return render(request, 'depart_edit.html', {'depart': depart})


# ============ 用户管理 ============

def user_list(request):
    """ 用户列表：分页查询员工并渲染到模板 """
    queryset = UserInfo.objects.all().order_by('id')     # 按ID排序，保证分页数据稳定
    page_object = Pagination(request, queryset)          # 分页处理（默认每页10条）
    return render(request, 'user_list.html', {
        'user_list': page_object.page_queryset,          # 当前页的数据
        'page_str': page_object.html(),                  # 分页条HTML
    })


def user_add(request):
    """ 新建用户（手动表单）：逐个字段从POST取值，手动写入数据库 """
    if request.method == "POST":
        UserInfo.objects.create(
            name=request.POST.get('name'),
            password=request.POST.get('password'),
            age=request.POST.get('age'),
            account=request.POST.get('account'),
            create_time=request.POST.get('create_time'),
            gender=request.POST.get('gender'),
            depart_id=request.POST.get('depart'),    # 外键字段赋值用 depart_id
        )
        return redirect('/user/list/')
    depart_list = Department.objects.all()   # 部门下拉框的数据来源
    return render(request, 'user_add.html', {'depart_list': depart_list})


def user_model_form_add(request):
    """ 新建用户（ModelForm）：字段校验、样式、保存都由Form类统一处理 """
    if request.method == "POST":
        form = UserModelForm(data=request.POST)
        if form.is_valid():                  # 校验（如用户名至少3个字符）
            form.save()                      # ModelForm自动映射字段写入数据库
            return redirect('/user/list/')
    form = UserModelForm()
    return render(request, 'user_model_form_add.html', {'form': form})


def depart_delete(request, nid):
    """ 删除部门并重新排序ID """
    # 删除指定部门
    Department.objects.filter(id=nid).delete()
    # 重新排序剩余部门ID
    queryset = list(Department.objects.all().order_by('id'))
    id_mapping = {}
    for index, depart in enumerate(queryset, start=1):
        id_mapping[depart.id] = index
    with connection.cursor() as cursor:
        # 临时关闭外键检查，避免更新ID时被引用约束阻断
        cursor.execute("SET FOREIGN_KEY_CHECKS=0")
        for old_id, new_id in id_mapping.items():
            if old_id != new_id:
                # 更新部门表ID
                cursor.execute(
                    "UPDATE app01_department SET id=%s WHERE id=%s",
                    [new_id, old_id],
                )
                # 同步更新员工表外键引用，保持关联正确
                cursor.execute(
                    "UPDATE app01_userinfo SET depart_id=%s WHERE depart_id=%s",
                    [new_id, old_id],
                )
        # 重置自增计数器，使下次新增的ID从当前最大值+1开始
        cursor.execute(
            "ALTER TABLE app01_department AUTO_INCREMENT = %s",
            [len(queryset) + 1],
        )
        cursor.execute("SET FOREIGN_KEY_CHECKS=1")
    return redirect('/depart/list/')


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
