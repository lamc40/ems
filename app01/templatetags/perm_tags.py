""" 自定义模板标签：权限过滤器

用法：
    {% load perm_tags %}
    {% if request.user|has_perm:"depart.add" %}
        <a href="/depart/add/">新增部门</a>
    {% endif %}
"""
from django import template

register = template.Library()


@register.filter(name='has_perm')
def has_perm(user, perm_code):
    """ 过滤器：判断用户是否拥有某权限码

    能处理 Django 匿名用户、非 User 模型对象等边界情况，
    在列表页对非登录主体（如 UserInfo）调用时返回 False。
    """
    try:
        if user is None:
            return False
        if not getattr(user, 'is_authenticated', False):
            return False
        if getattr(user, 'is_superuser', False):
            return True
        role = getattr(user, 'role', None)
        if not role:
            return False
        return role.permissions.filter(code=perm_code).exists()
    except Exception:
        return False


@register.filter(name='in_role')
def in_role(user, role_code):
    """ 过滤器：判断用户是否属于某角色 """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return getattr(user.role, 'code', '') == role_code


@register.filter(name='is_staff_or_above')
def is_staff_or_above(user, _=None):
    """ 过滤器：是否为后台管理员 """
    return bool(user and user.is_authenticated and user.is_staff)
