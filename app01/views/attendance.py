""" 考勤管理视图：列表/新增/批量录入/编辑/删除

考勤状态由上下班时间自动计算（见 models.Attendance.calculate_status），
用户在表单中只需要填写日期、上班打卡时间、下班打卡时间。
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q

from app01.models import Attendance, UserInfo
from app01.utils.pagination import Pagination


def _is_admin_user(user):
    """ 是否是管理者（超级管理员或部门管理员）—— 以 role 为唯一可信身份源 """
    if user.is_superuser:
        return True
    return user.role and user.role.name in ('超级管理员', '部门管理员')


def attendance_list(request):
    """ 考勤列表：支持按员工姓名搜索 + 按日期范围筛选 + 分页
    权限：管理员看全部，普通员工只看自己的
    """
    search = request.GET.get('search', '').strip()
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    queryset = Attendance.objects.select_related('employee').all()

    # 行级权限：普通员工只能看自己的考勤（以 role 为准）
    if not _is_admin_user(request.user):
        queryset = queryset.filter(employee__user=request.user)

    if search:
        queryset = queryset.filter(employee__name__contains=search)
    if date_from:
        queryset = queryset.filter(date__gte=date_from)
    if date_to:
        queryset = queryset.filter(date__lte=date_to)

    page_object = Pagination(request, queryset, page_size=15)
    return render(request, 'attendance_list.html', {
        'attendance_list': page_object.page_queryset,
        'page_str': page_object.html(),
        'search': search,
        'date_from': date_from,
        'date_to': date_to,
    })


def attendance_add(request):
    """ 单条考勤录入：填写后自动计算状态 """
    employees = UserInfo.objects.all()
    if request.method == "POST":
        employee_id = request.POST.get('employee')
        date = request.POST.get('date')
        morning_time = request.POST.get('morning_time') or None
        evening_time = request.POST.get('evening_time') or None
        remark = request.POST.get('remark', '')

        att = Attendance.objects.create(
            employee_id=employee_id,
            date=date,
            morning_time=morning_time,
            evening_time=evening_time,
            remark=remark,
        )
        att.calculate_status()   # 自动计算考勤状态
        return redirect('/attendance/list/')

    return render(request, 'attendance_add.html', {'employees': employees})


def attendance_batch(request):
    """ 批量录入：选择日期后，为所有员工创建考勤记录（默认状态待计算） """
    if request.method == "POST":
        date = request.POST.get('date')
        employee_ids = request.POST.getlist('employees')
        for emp_id in employee_ids:
            att, _ = Attendance.objects.get_or_create(
                employee_id=emp_id, date=date,
                defaults={'status': 'absent'},
            )
        return redirect('/attendance/list/')

    employees = UserInfo.objects.all()
    return render(request, 'attendance_batch.html', {'employees': employees})


def attendance_edit(request, nid):
    """ 编辑考勤：修改时间后自动重新计算状态 """
    att = get_object_or_404(Attendance, id=nid)
    employees = UserInfo.objects.all()

    if request.method == "POST":
        att.employee_id = request.POST.get('employee')
        att.date = request.POST.get('date')
        att.morning_time = request.POST.get('morning_time') or None
        att.evening_time = request.POST.get('evening_time') or None
        att.remark = request.POST.get('remark', '')
        att.save()
        att.calculate_status()
        return redirect('/attendance/list/')

    return render(request, 'attendance_edit.html', {
        'attendance': att, 'employees': employees,
    })


def attendance_delete(request, nid):
    """ 删除考勤记录 """
    Attendance.objects.filter(id=nid).delete()
    return redirect('/attendance/list/')
