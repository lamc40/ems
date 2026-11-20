""" 全局模板上下文：注入登录用户和管理员列表 """
from django.contrib.auth import get_user_model

User = get_user_model()


def inject_admin_list(request):
    """ 每次请求都把全部管理员列表传给模板，layout.html 的下拉菜单需要 """
    return {
        'admin_all': User.objects.filter(is_staff=True).order_by('id'),
    }
