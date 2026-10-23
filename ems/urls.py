from django.contrib import admin
from django.urls import path

from app01.views import depart, pretty, user

urlpatterns = [
    path('admin/', admin.site.urls),  # Django自带后台

    # 部门管理
    path('depart/list/', depart.depart_list, name='depart_list'),                 # 部门列表
    path('depart/add/', depart.depart_add, name='depart_add'),                    # 新增部门
    path('depart/add2/', depart.depart_add2, name='depart_add2'),                 # 新增部门（版本2）
    path('depart/edit/<int:nid>/', depart.depart_edit, name='depart_edit'),       # 编辑部门
    path('depart/delete/<int:nid>/', depart.depart_delete, name='depart_delete'), # 删除部门并重排ID

    # 用户管理
    path('user/list/', user.user_list, name='user_list'),                                    # 用户列表
    path('user/add/', user.user_add, name='user_add'),                                       # 新建用户（手动表单）
    path('user/model/form/add/', user.user_model_form_add, name='user_model_form_add'),      # 新建用户（ModelForm）

    # 靓号管理
    path('pretty/list/', pretty.pretty_list, name='pretty_list'),                 # 靓号列表（含搜索）
    path('pretty/add/', pretty.pretty_add, name='pretty_add'),                    # 新建靓号
    path('pretty/edit/<int:nid>/', pretty.pretty_edit, name='pretty_edit'),       # 编辑靓号，<int:nid>接收路径中的ID
    path('pretty/delete/<int:nid>/', pretty.pretty_delete, name='pretty_delete'), # 删除靓号并重排ID
]
