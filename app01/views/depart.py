""" 部门管理视图：列表（分页）/ 新增 / 编辑 / 删除 """
from django.db import connection
from django.shortcuts import render, redirect, get_object_or_404

from app01.models import Department
from app01.utils.pagination import Pagination


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
