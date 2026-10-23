""" 用户管理视图：列表（分页）/ 新建（手动表单、ModelForm两种写法） """
from django.shortcuts import render, redirect

from app01.models import Department, UserInfo
from app01.utils.form import UserModelForm
from app01.utils.pagination import Pagination


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
