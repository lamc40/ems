""" 员工管理视图：列表（搜索+部门筛选+分页）/ 新建（ModelForm）/ 编辑

性能优化：select_related('depart') 消除 N+1 查询（列表页 depart 外键引用）。
"""
from django.shortcuts import render, redirect, get_object_or_404

from app01.models import Department, UserInfo
from app01.utils.form import UserModelForm, UserEditModelForm
from app01.utils.pagination import Pagination


def user_list(request):
    """ 员工列表：姓名模糊搜索 + 部门筛选 + 分页 + select_related 优化 """
    search = request.GET.get('search', '').strip()
    depart_id = request.GET.get('depart', '').strip()

    queryset = UserInfo.objects.select_related('depart').all()

    if search:
        queryset = queryset.filter(name__contains=search)
    if depart_id and depart_id.isdecimal():
        queryset = queryset.filter(depart_id=int(depart_id))

    page_object = Pagination(request, queryset)
    return render(request, 'user_list.html', {
        'user_list': page_object.page_queryset,
        'page_str': page_object.html(),
        'search': search,
        'depart_id': depart_id,
        'depart_list': Department.objects.all(),
    })


def user_add(request):
    """ 新建员工（手动表单）：逐个字段从 POST 取值 """
    if request.method == "POST":
        UserInfo.objects.create(
            name=request.POST.get('name'),
            age=request.POST.get('age'),
            account=request.POST.get('account'),
            create_time=request.POST.get('create_time'),
            gender=request.POST.get('gender'),
            depart_id=request.POST.get('depart'),
            mobile=request.POST.get('mobile') or None,
        )
        return redirect('/user/list/')
    depart_list = Department.objects.all()
    return render(request, 'user_add.html', {'depart_list': depart_list})


def user_model_form_add(request):
    """ 新建员工（ModelForm）：字段校验 + Bootstrap 样式统一 """
    if request.method == "POST":
        form = UserModelForm(data=request.POST, files=request.FILES)
        if form.is_valid():
            form.save()
            return redirect('/user/list/')
    else:
        form = UserModelForm()
    return render(request, 'user_model_form_add.html', {'form': form})


def user_edit(request, nid):
    """ 编辑员工（ModelForm）：手机号唯一性校验自动排除自身 """
    row = get_object_or_404(UserInfo, id=nid)
    if request.method == "POST":
        form = UserEditModelForm(data=request.POST, instance=row, files=request.FILES)
        if form.is_valid():
            form.save()
            return redirect('/user/list/')
    else:
        form = UserEditModelForm(instance=row)
    return render(request, 'user_model_form_add.html', {'form': form, 'title': f'编辑员工 - {row.name}'})
