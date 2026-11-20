""" 薪资管理视图：列表/新增/编辑/删除 + 按月统计

实发工资由 Salary.save() 自动计算（base + bonus - deduction），
视图中用 commit=False + obj.save() 即可。
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, Q

from app01.models import Salary, UserInfo
from app01.utils.pagination import Pagination


def _is_admin_user(user):
    """ 是否是管理者（超级管理员或部门管理员）—— 以 role 为唯一可信身份源 """
    if user.is_superuser:
        return True
    return user.role and user.role.name in ('超级管理员', '部门管理员')


def salary_list(request):
    """ 薪资列表：支持按月份和员工姓名筛选 + 统计选定月份薪资总额
    权限：管理员看全部，普通员工只看自己的
    """
    month = request.GET.get('month', '').strip()
    search = request.GET.get('search', '').strip()

    queryset = Salary.objects.select_related('employee').all()

    # 行级权限：普通员工只能看自己的工资（以 role 为准，而非不可靠的 is_staff）
    if not _is_admin_user(request.user):
        queryset = queryset.filter(employee__user=request.user)

    if month:
        queryset = queryset.filter(month=month)
    if search:
        queryset = queryset.filter(employee__name__contains=search)

    # 统计总额（当前筛选条件下）
    total_amount = queryset.aggregate(total=Sum('total'))['total'] or 0
    record_count = queryset.count()

    page_object = Pagination(request, queryset, page_size=15)
    return render(request, 'salary_list.html', {
        'salary_list': page_object.page_queryset,
        'page_str': page_object.html(),
        'month': month,
        'search': search,
        'total_amount': total_amount,
        'record_count': record_count,
    })


def salary_add(request):
    """ 新增薪资：total 由 Salary.save() 自动计算 """
    employees = UserInfo.objects.all()
    if request.method == "POST":
        obj = Salary.objects.create(
            employee_id=request.POST.get('employee'),
            month=request.POST.get('month'),
            base_salary=request.POST.get('base_salary') or 0,
            bonus=request.POST.get('bonus') or 0,
            deduction=request.POST.get('deduction') or 0,
            remark=request.POST.get('remark', ''),
        )
        # 不能重复（unique_together），让用户编辑
        return redirect('/salary/list/')

    return render(request, 'salary_add.html', {'employees': employees})


def salary_edit(request, nid):
    """ 编辑薪资：修改后 total 自动重算
    行级权限：普通员工不能编辑别人的工资
    """
    obj = get_object_or_404(Salary, id=nid)
    # 行级权限校验：普通员工不能编辑别人的工资
    if not _is_admin_user(request.user):
        if obj.employee.user_id != request.user.id:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden('你无权编辑他人的薪资')

    employees = UserInfo.objects.all()

    if request.method == "POST":
        obj.base_salary = request.POST.get('base_salary') or 0
        obj.bonus = request.POST.get('bonus') or 0
        obj.deduction = request.POST.get('deduction') or 0
        obj.remark = request.POST.get('remark', '')
        obj.save()   # 自动重算 total
        return redirect('/salary/list/')

    return render(request, 'salary_edit.html', {
        'salary': obj, 'employees': employees,
    })


def salary_delete(request, nid):
    """ 删除薪资记录
    行级权限：普通员工不能删别人的工资
    """
    obj = get_object_or_404(Salary, id=nid)
    if not _is_admin_user(request.user):
        if obj.employee.user_id != request.user.id:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden('你无权删除他人的薪资')
    obj.delete()
    return redirect('/salary/list/')
