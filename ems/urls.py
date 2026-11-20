from django.contrib import admin as dj_admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

from app01.views import admin, depart, pretty, task, user
from app01.views import attendance, salary, notice, dashboard, ai
from app01.views import order, chart, upload, city


def home(request):
    """根路径重定向：未登录→登录页，已登录→仪表盘"""
    if request.user.is_authenticated:
        return redirect('/dashboard/')
    return redirect('/login/')


urlpatterns = [
    # 根路径
    path('', home, name='home'),

    # Django 自带后台（改前缀避免与业务admin冲突）
    path('djadmin/', dj_admin.site.urls),

    # ===== 认证 =====
    path('login/', admin.login_view, name='login'),
    path('logout/', admin.logout_view, name='logout'),
    path('admin/switch/<int:nid>/', admin.switch, name='admin_switch'),
    path('admin/code/', admin.code_img, name='admin_code'),

    # ===== 管理员管理 =====
    path('admin/list/', admin.admin_list, name='admin_list'),
    path('admin/add/', admin.admin_add, name='admin_add'),
    path('admin/edit/<int:nid>/', admin.admin_edit, name='admin_edit'),
    path('admin/delete/<int:nid>/', admin.admin_delete, name='admin_delete'),
    path('admin/reset/<int:nid>/', admin.admin_reset, name='admin_reset'),

    # ===== 部门管理 =====
    path('depart/list/', depart.depart_list, name='depart_list'),
    path('depart/add/', depart.depart_add, name='depart_add'),
    path('depart/add2/', depart.depart_add2, name='depart_add2'),
    path('depart/edit/<int:nid>/', depart.depart_edit, name='depart_edit'),
    path('depart/delete/<int:nid>/', depart.depart_delete, name='depart_delete'),
    path('depart/multi/', depart.depart_multi, name='depart_multi'),

    # ===== 员工管理 =====
    path('user/list/', user.user_list, name='user_list'),
    path('user/add/', user.user_add, name='user_add'),
    path('user/model/form/add/', user.user_model_form_add, name='user_model_form_add'),

    # ===== 靓号管理 =====
    path('pretty/list/', pretty.pretty_list, name='pretty_list'),
    path('pretty/add/', pretty.pretty_add, name='pretty_add'),
    path('pretty/edit/<int:nid>/', pretty.pretty_edit, name='pretty_edit'),
    path('pretty/delete/<int:nid>/', pretty.pretty_delete, name='pretty_delete'),

    # ===== 考勤管理（新） =====
    path('attendance/list/', attendance.attendance_list, name='attendance_list'),
    path('attendance/add/', attendance.attendance_add, name='attendance_add'),
    path('attendance/add/batch/', attendance.attendance_batch, name='attendance_batch'),
    path('attendance/edit/<int:nid>/', attendance.attendance_edit, name='attendance_edit'),
    path('attendance/delete/<int:nid>/', attendance.attendance_delete, name='attendance_delete'),

    # ===== 薪资管理（新） =====
    path('salary/list/', salary.salary_list, name='salary_list'),
    path('salary/add/', salary.salary_add, name='salary_add'),
    path('salary/edit/<int:nid>/', salary.salary_edit, name='salary_edit'),
    path('salary/delete/<int:nid>/', salary.salary_delete, name='salary_delete'),

    # ===== 公告管理（新） =====
    path('notice/list/', notice.notice_list, name='notice_list'),
    path('notice/add/', notice.notice_add, name='notice_add'),
    path('notice/edit/<int:nid>/', notice.notice_edit, name='notice_edit'),
    path('notice/delete/<int:nid>/', notice.notice_delete, name='notice_delete'),
    path('notice/top/<int:nid>/', notice.notice_toggle_top, name='notice_toggle_top'),

    # ===== 任务管理（AJAX 示例 + Excel 批量导入） =====
    path('task/list/', task.task_list, name='task_list'),
    path('task/ajax/submit/', task.task_ajax_submit, name='task_ajax_submit'),
    path('task/ajax/delete/', task.task_ajax_delete, name='task_ajax_delete'),
    path('task/template/', task.task_template, name='task_template'),
    path('task/import/', task.task_import, name='task_import'),

    # ===== 数据统计可视化（新） =====
    path('dashboard/', dashboard.dashboard, name='dashboard'),
    path('api/dashboard/department_stats/', dashboard.api_department_stats, name='api_dept_stats'),
    path('api/dashboard/salary_trend/', dashboard.api_salary_trend, name='api_salary_trend'),

    # ===== AI 智能助手 =====
    path('ai/', ai.ai_index, name='ai_index'),
    path('ai/jd/', ai.generate_jd),
    path('ai/knowledge/', ai.knowledge_qa),
    path('ai/review/', ai.employee_review),
    path('ai/chat/', ai.chat_stream),
    path('ai/notice/', ai.notice_qa),
    path('ai/meme/', ai.meme_recognize),          # 梗识别 API
    path('ai/meme/list/', ai.meme_list),          # 梗库列表
    path('ai/meme/add/', ai.meme_add),            # 新增梗
    path('ai/meme/toggle/', ai.meme_toggle),      # 启停切换
    path('ai/meme/delete/', ai.meme_delete),      # 删除梗

    # ===== 订单管理（教程 18 章） =====
    path('order/list/', order.order_list),
    path('order/add/', order.order_add),
    path('order/delete/', order.order_delete),
    path('order/detail/', order.order_detail),
    path('order/edit/', order.order_edit),

    # ===== 数据统计 ECharts（教程 19 章） =====
    path('chart/list/', chart.chart_list),
    path('chart/bar/', chart.chart_bar),
    path('chart/pie/', chart.chart_pie),
    path('chart/line/', chart.chart_line),
    path('chart/highcharts/', chart.highcharts),

    # ===== 文件上传（教程 20 章） =====
    path('upload/list/', upload.upload_list),
    path('upload/form/', upload.upload_form),
    path('upload/modal/form/', upload.upload_modal_form),
    path('tt/', upload.tt),

    # ===== 城市列表（教程 21 章） =====
    path('city/list/', city.city_list),
    path('city/add/', city.city_add),
]

# 媒体文件服务（开发模式下）
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
