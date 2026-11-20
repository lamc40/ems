""" 数据统计可视化（ECharts）

后端用 ORM 聚合数据，前端 ECharts 通过 AJAX 取 JSON 渲染图表。
提供两个接口：
- /api/dashboard/department_stats/ —— 部门人数分布饼图
- /api/dashboard/salary_trend/ —— 近6个月薪资趋势折线图
"""
from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth

from app01.models import Department, UserInfo, Salary, Notice


def dashboard(request):
    """ 仪表盘主页：ECharts 通过 AJAX 取数据渲染 """
    # 汇总卡片数据
    data = {
        'dept_count': Department.objects.count(),
        'emp_count': UserInfo.objects.count(),
        'notice_count': Notice.objects.count(),
        'salary_total': Salary.objects.aggregate(total=Sum('total'))['total'] or 0,
    }
    return render(request, 'dashboard.html', data)


def api_department_stats(request):
    """ 接口：部门人数分布（饼图数据）

    返回格式：[{"name": "技术部", "value": 12}, ...]
    """
    stats = list(
        Department.objects.annotate(
            count=Count('employees')
        ).values('title', 'count')
    )
    data = [{'name': s['title'], 'value': s['count']} for s in stats]
    return JsonResponse({'status': True, 'data': data})


def api_salary_trend(request):
    """ 接口：近6个月薪资总额趋势（折线图数据）

    返回格式：
    {
      "months": ["2025-05", "2025-06", ...],
      "totals": [125000, 132000, ...]
    }
    """
    stats = list(
        Salary.objects.values('month')
        .annotate(total=Sum('total'))
        .order_by('month')[:12]   # 最多返回12个月
    )
    months = [s['month'] for s in stats]
    totals = [float(s['total'] or 0) for s in stats]
    return JsonResponse({
        'status': True,
        'data': {'months': months, 'totals': totals},
    })
