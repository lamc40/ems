""" 认证与权限中间件：两步校验

1. AuthMiddleware —— 统一登录校验（白名单 + session 检查）
2. PermissionMiddleware —— RBAC 接口级权限校验（按 request.path 匹配权限码）

顺序：AuthMiddleware 必须在 SessionMiddleware 之后；
      PermissionMiddleware 在 AuthMiddleware 之后（确保已登录才校验权限）。
"""
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.http import JsonResponse

User = get_user_model()


# ==================== 1. 登录校验 ====================

WHITE_LIST = [
    '/login/',          # 登录页本身
    '/logout/',         # 登出
    '/admin/code/',     # 图片验证码（登录页用）
    '/djadmin/',        # Django 自带后台（它自己有认证）
    '/static/',         # 静态资源
    '/media/',          # 媒体资源（头像等）
    '/favicon.ico',
]


class AuthMiddleware:
    """ 统一登录校验中间件：未登录直接重定向到登录页 """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info

        # 白名单直接放行
        for url in WHITE_LIST:
            if path.startswith(url):
                return self.get_response(request)

        # 检查用户是否在 request.user 上（AuthenticationMiddleware 已做）
        # 但 Django 的 request.user 是 AnonymousUser 未登录
        if request.user.is_authenticated:
            return self.get_response(request)

        # 未登录
        if request.method == 'GET':
            return redirect('/login/?next={}'.format(path))
        return redirect('/login/')


# ==================== 2. RBAC 权限校验 ====================

# 路径前缀 → 所需权限码的映射
# 格式：(路径前缀, 权限码)
PATH_PERMISSION_MAP = [
    ('/admin/list/', 'admin.view'),
    ('/admin/add/', 'admin.add'),
    ('/admin/edit/', 'admin.edit'),
    ('/admin/delete/', 'admin.delete'),
    ('/admin/reset/', 'admin.edit'),
    ('/depart/list/', 'depart.view'),
    ('/depart/add/', 'depart.add'),
    ('/depart/edit/', 'depart.edit'),
    ('/depart/delete/', 'depart.delete'),
    ('/user/list/', 'user.view'),
    ('/user/add/', 'user.add'),
    ('/user/model/', 'user.add'),
    ('/pretty/', 'pretty.view'),
    ('/attendance/list/', 'attendance.view'),
    ('/attendance/', 'attendance.add'),
    ('/salary/list/', 'salary.view'),
    ('/salary/', 'salary.add'),
    ('/notice/list/', 'notice.view'),
    ('/notice/add/', 'notice.add'),
    ('/notice/edit/', 'notice.edit'),
    ('/notice/delete/', 'notice.delete'),
    ('/dashboard/', 'dashboard.view'),
]


class PermissionMiddleware:
    """ RBAC 权限校验：登录后检查用户是否有当前接口所需权限

    - 超级管理员（is_superuser=True）直接放行
    - 其他角色按 PATH_PERMISSION_MAP 匹配后检查权限码
    - 校验失败返回 403（页面请求）或 JSON 错误（AJAX 请求）
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 未登录由 AuthMiddleware 处理
        if not request.user.is_authenticated:
            return self.get_response(request)

        # 超级管理员直接放行
        if request.user.is_superuser:
            return self.get_response(request)

        path = request.path_info
        for prefix, perm_code in PATH_PERMISSION_MAP:
            if path.startswith(prefix):
                if not request.user.has_perm_code(perm_code):
                    # AJAX 请求返回 JSON
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({'status': False, 'message': '无权限访问'}, status=403)
                    # 页面请求返回 403
                    from django.http import HttpResponseForbidden
                    return HttpResponseForbidden('权限不足，请联系管理员')
                break

        return self.get_response(request)
