""" 任务管理：列表页 + AJAX 异步提交 + Excel 批量导入（T9/T17）"""
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt

import openpyxl

from app01.models import Task, UserInfo
from app01.utils.pagination import Pagination


def task_list(request):
    """ 任务列表 + AJAX 异步表单页面 """
    queryset = Task.objects.select_related('owner').all().order_by('level')
    page_object = Pagination(request, queryset, page_size=3)
    employees = UserInfo.objects.all()
    return render(request, 'task_list.html', {
        'task_list': page_object.page_queryset,
        'page_str': page_object.html(),
        'employees': employees,
        'LEVEL_CHOICES': Task.LEVEL_CHOICES,
        'STATUS_CHOICES': Task.STATUS_CHOICES,
    })


@csrf_exempt
def task_ajax_submit(request):
    """ AJAX 提交接口：校验 + 保存任务，返回 JSON（不刷新页面）

    返回格式：
        成功：{"status": true, "data": {...}, "message": "创建成功"}
        失败：{"status": false, "errors": {"title": ["不能为空"], ...}}
    """
    if request.method != 'POST':
        return JsonResponse({'status': False, 'message': '仅支持 POST'}, status=405)

    title = request.POST.get('title', '').strip()
    level = request.POST.get('level', 'P2')
    detail = request.POST.get('detail', '').strip()
    owner_id = request.POST.get('owner') or None

    # 手动校验（演示"校验错误回显"）
    errors = {}
    if not title:
        errors['title'] = '标题不能为空'
    elif len(title) > 100:
        errors['title'] = '标题不能超过 100 字符'
    if level not in dict(Task.LEVEL_CHOICES):
        errors['level'] = '级别无效'
    if detail and len(detail) > 1000:
        errors['detail'] = '详情不能超过 1000 字符'

    if errors:
        return JsonResponse({'status': False, 'errors': errors})

    task = Task.objects.create(
        title=title, level=level, detail=detail,
        owner_id=owner_id if owner_id and owner_id.isdecimal() else None,
    )
    return JsonResponse({
        'status': True,
        'message': '创建成功',
        'data': {
            'id': task.id,
            'title': task.title,
            'level': task.get_level_display(),
            'owner': task.owner.name if task.owner else '未分配',
            'created_at': task.created_at.strftime('%Y-%m-%d %H:%M'),
        },
    })


@csrf_exempt
def task_ajax_delete(request):
    """ AJAX 删除任务 """
    task_id = request.POST.get('id')
    if task_id and task_id.isdecimal():
        deleted, _ = Task.objects.filter(id=int(task_id)).delete()
        if deleted:
            return JsonResponse({'status': True, 'message': '已删除'})
    return JsonResponse({'status': False, 'message': '删除失败'}, status=400)


def task_template(request):
    """ 下载 Excel 导入模板（带一行示例数据）"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "任务导入模板"
    # 表头（中文列名，对应用户友好输入）
    headers = ['标题', '级别', '详情', '负责人姓名', '状态']
    ws.append(headers)
    # 示例行（第 2 行）
    ws.append(['完成 Q4 述职报告', 'P1', '整理全年项目数据并输出 PPT', '郭栋梁', 'pending'])
    # 列宽
    widths = [30, 10, 50, 15, 12]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="task_import_template.xlsx"'
    wb.save(response)
    return response


@csrf_exempt
def task_import(request):
    """ Excel 批量导入任务
    模板列：标题(必填) | 级别(P0/P1/P2/P3) | 详情 | 负责人姓名 | 状态(pending/doing/done)
    从第 2 行开始读（跳过表头）
    """
    if request.method != 'POST':
        return JsonResponse({'status': False, 'message': '仅支持 POST'}, status=405)

    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'status': False, 'message': '请先选择 Excel 文件'})

    if not file.name.endswith(('.xlsx', '.xls')):
        return JsonResponse({'status': False, 'message': '只支持 .xlsx / .xls 文件'})

    try:
        wb = openpyxl.load_workbook(file)
    except Exception as e:
        return JsonResponse({'status': False, 'message': f'Excel 解析失败：{e}'})

    ws = wb.active
    errors = []
    created_count = 0
    LEVEL_MAP = dict(Task.LEVEL_CHOICES)   # {'P0': '紧急', ...}
    STATUS_MAP = dict(Task.STATUS_CHOICES)  # {'pending': '待办', ...}
    VALID_LEVELS = set(LEVEL_MAP.keys())
    VALID_STATUSES = set(STATUS_MAP.keys())

    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or all(c is None or str(c).strip() == '' for c in row):
            continue  # 跳过空行

        title = str(row[0]).strip() if row[0] else ''
        level = str(row[1]).strip().upper() if row[1] else 'P2'
        detail = str(row[2]).strip() if row[2] else ''
        owner_name = str(row[3]).strip() if len(row) > 3 and row[3] else ''
        status = str(row[4]).strip().lower() if len(row) > 4 and row[4] else 'pending'

        row_errors = []
        if not title:
            row_errors.append('标题必填')
        elif len(title) > 100:
            row_errors.append('标题超过 100 字')
        if level not in VALID_LEVELS:
            # 允许用户写中文"紧急/高/中/低"
            zh_to_code = {v: k for k, v in LEVEL_MAP.items()}
            if level in zh_to_code:
                level = zh_to_code[level]
            else:
                row_errors.append(f'级别无效（应为 P0/P1/P2/P3 或 紧急/高/中/低）')
        if status not in VALID_STATUSES:
            zh_to_code = {v: k for k, v in STATUS_MAP.items()}
            if status in zh_to_code:
                status = zh_to_code[status]
            else:
                row_errors.append(f'状态无效（应为 pending/doing/done 或 待办/进行中/已完成）')

        owner = None
        if owner_name:
            owner = UserInfo.objects.filter(name=owner_name).first()
            if not owner:
                row_errors.append(f'负责人 "{owner_name}" 不存在')

        if row_errors:
            errors.append(f'第 {row_idx} 行：{"；".join(row_errors)}')
            continue

        Task.objects.create(
            title=title, level=level, detail=detail,
            owner=owner, status=status,
        )
        created_count += 1

    wb.close()

    if errors and created_count == 0:
        return JsonResponse({'status': False, 'message': '导入失败', 'errors': errors})

    msg = f'导入成功 {created_count} 条'
    if errors:
        msg += f'，{len(errors)} 行有问题（已跳过）'
    return JsonResponse({'status': True, 'message': msg, 'errors': errors})
