""" 用户管理视图：登录 / 登出 / 切换身份 + 列表（搜索+分页）/ 新建 / 编辑 / 重置密码

认证改用 Django 内置 authenticate / login / logout，密码用 set_password 哈希存储。
"""
import io

from django.contrib.auth import authenticate, login, logout, get_user_model
from django.shortcuts import render, redirect, get_object_or_404

from app01.models import Role
from app01.utils.check_code import check_code
from app01.utils.form import AdminModelForm, AdminEditModelForm, AdminResetModelForm
from app01.utils.pagination import Pagination

User = get_user_model()


def code_img(request):
    """ 图片验证码：生成随机验证码图片 + 把验证码字符串存 session """
    img, code_str = check_code()
    request.session['code'] = code_str.upper()
    buf = io.BytesIO()
    img.save(buf, format='png')
    from django.http import HttpResponse
    return HttpResponse(buf.getvalue(), content_type='image/png')


def login_view(request):
    """ 登录：校验验证码 → 校验用户名 + 密码（Django authenticate）

    密码验证由 Django 内部完成：authenticate 会用 check_password 比对
    数据库存的 PBKDF2 哈希值与用户提交的明文。
    """
    error = ""
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        code = request.POST.get("code", "").strip()

        # 0. 先校验验证码（不区分大小写）
        session_code = request.session.get('code', '').upper()
        if not code or code.upper() != session_code:
            error = "验证码错误"
        elif not username or not password:
            error = "用户名和密码不能为空"
        else:
            # 1. Django authenticate —— 内部用 PBKDF2 校验密码
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)   # 写入 session
                request.session.pop('code', None)   # 清除用过的验证码
                # 登录成功后跳回原页面（如有 next 参数）
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url:
                    return redirect(next_url)
                # 根据角色动态跳转：只有超级管理员能进用户管理页
                if user.is_superuser or user.has_perm_code('admin.view'):
                    return redirect('/admin/list/')
                if user.has_perm_code('dashboard.view'):
                    return redirect('/dashboard/')
                if user.has_perm_code('attendance.view'):
                    return redirect('/attendance/list/')
                return redirect('/notice/list/')
            error = "用户名或密码错误"

    return render(request, 'login.html', {"error": error})


def logout_view(request):
    """ 登出：调用 Django logout 清空 session """
    logout(request)
    return redirect('/login/')


def switch(request, nid):
    """ 切换身份（调试/演示用）：直接把 session 改成目标用户 """
    obj = get_object_or_404(User, id=nid)
    login(request, obj)
    next_url = request.META.get('HTTP_REFERER', '/admin/list/')
    return redirect(next_url)


# ==================== 管理员 CRUD ====================

def admin_list(request):
    """ 管理员列表（含用户名模糊搜索 + 分页 + select_related 优化 role/depart 外键） """
    search = request.GET.get('search', '')
    queryset = User.objects.filter(is_staff=True).select_related('role', 'depart').order_by('id')
    if search:
        queryset = queryset.filter(username__contains=search)
    page_object = Pagination(request, queryset)
    return render(request, 'admin_list.html', {
        'admin_list': page_object.page_queryset,
        'search': search,
        'page_str': page_object.html(),
    })


def admin_add(request):
    """ 新建管理员：AdminModelForm 会自动 set_password 哈希 """
    title = "新建管理员"
    if request.method == "POST":
        form = AdminModelForm(data=request.POST)
        if form.is_valid():
            form.save()
            return redirect('/admin/list/')
    else:
        form = AdminModelForm()
    return render(request, 'change.html', {'form': form, 'title': title})


def admin_edit(request, nid):
    """ 编辑管理员：AdminEditModelForm 只改 username/role/phone """
    row = get_object_or_404(User, id=nid)
    title = f"编辑管理员 - {row.username}"
    if request.method == "POST":
        form = AdminEditModelForm(data=request.POST, instance=row)
        if form.is_valid():
            form.save()
            return redirect('/admin/list/')
    else:
        form = AdminEditModelForm(instance=row)
    return render(request, 'change.html', {'form': form, 'title': title})


def admin_delete(request, nid):
    """ 删除管理员 """
    User.objects.filter(id=nid).delete()
    return redirect('/admin/list/')


def admin_reset(request, nid):
    """ 重置密码：AdminResetModelForm 会自动 set_password 新密码 """
    row = get_object_or_404(User, id=nid)
    title = f"重置密码 - {row.username}"
    if request.method == "POST":
        form = AdminResetModelForm(data=request.POST, instance=row)
        if form.is_valid():
            form.save()
            return redirect('/admin/list/')
    else:
        form = AdminResetModelForm()
    return render(request, 'change.html', {'form': form, 'title': title})
