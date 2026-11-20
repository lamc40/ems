""" 数据初始化命令：一键创建角色/权限/演示数据

用法：python manage.py init_data
      python manage.py init_data --reset   # 先清空再重建（谨慎使用）
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from app01.models import (
    Role, Permission, Department, UserInfo,
    Attendance, Salary, Notice, Task,
)

User = get_user_model()


# ==================== RBAC 权限定义 ====================

PERMISSIONS = [
    # 部门管理
    ('depart.view', '查看部门', '部门管理'),
    ('depart.add', '新增部门', '部门管理'),
    ('depart.edit', '编辑部门', '部门管理'),
    ('depart.delete', '删除部门', '部门管理'),
    # 员工管理
    ('user.view', '查看员工', '员工管理'),
    ('user.add', '新增员工', '员工管理'),
    ('user.edit', '编辑员工', '员工管理'),
    ('user.delete', '删除员工', '员工管理'),
    # 管理员管理
    ('admin.view', '查看管理员', '管理员管理'),
    ('admin.add', '新增管理员', '管理员管理'),
    ('admin.edit', '编辑管理员', '管理员管理'),
    ('admin.delete', '删除管理员', '管理员管理'),
    # 考勤
    ('attendance.view', '查看考勤', '考勤管理'),
    ('attendance.add', '录入考勤', '考勤管理'),
    ('attendance.edit', '编辑考勤', '考勤管理'),
    ('attendance.delete', '删除考勤', '考勤管理'),
    # 薪资
    ('salary.view', '查看薪资', '薪资管理'),
    ('salary.add', '录入薪资', '薪资管理'),
    ('salary.edit', '编辑薪资', '薪资管理'),
    ('salary.delete', '删除薪资', '薪资管理'),
    # 公告
    ('notice.view', '查看公告', '公告管理'),
    ('notice.add', '发布公告', '公告管理'),
    ('notice.edit', '编辑公告', '公告管理'),
    ('notice.delete', '删除公告', '公告管理'),
    # 仪表盘
    ('dashboard.view', '查看数据统计', '数据统计'),
]


ROLE_PERMISSIONS = {
    '超级管理员': None,   # None = 所有权限
    '部门管理员': [
        'depart.view', 'depart.add', 'depart.edit',
        'user.view', 'user.add', 'user.edit',
        'attendance.view', 'attendance.add', 'attendance.edit', 'attendance.delete',
        'salary.view', 'salary.add', 'salary.edit', 'salary.delete',
        'notice.view', 'notice.add', 'notice.edit',
        'dashboard.view',
    ],
    '普通员工': [
        'depart.view',
        'user.view',
        'attendance.view',
        'salary.view',
        'notice.view',
        'dashboard.view',
    ],
}


class Command(BaseCommand):
    help = '一键初始化角色、权限和演示数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help='先清空所有业务表再重建（谨慎使用）',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write('⚠ 清空所有业务表...')
            Attendance.objects.all().delete()
            Salary.objects.all().delete()
            Notice.objects.all().delete()
            UserInfo.objects.all().delete()
            Department.objects.all().delete()
            User.objects.filter(is_staff=False).delete()
            Role.objects.all().delete()
            Permission.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('已清空'))

        # 1. 创建权限
        self.stdout.write('创建权限...')
        perm_map = {}
        for code, name, module in PERMISSIONS:
            perm, _ = Permission.objects.get_or_create(
                code=code, defaults={'name': name, 'module': module})
            perm_map[code] = perm
        self.stdout.write(f'  ✓ {len(PERMISSIONS)} 个权限')

        # 2. 创建角色
        self.stdout.write('创建角色...')
        role_map = {}
        for role_name, perm_codes in ROLE_PERMISSIONS.items():
            role, _ = Role.objects.get_or_create(
                name=role_name, defaults={'code': role_name, 'description': f'{role_name}角色'})
            if perm_codes is None:
                role.permissions.set(perm_map.values())   # 所有权限
            else:
                role.permissions.set([perm_map[c] for c in perm_codes if c in perm_map])
            role_map[role_name] = role
        self.stdout.write(f'  ✓ {len(ROLE_PERMISSIONS)} 个角色')

        # 3. 创建部门
        self.stdout.write('创建部门...')
        dept_map = {}
        for title in ['技术部', '产品部', '市场部', '人事部', '财务部']:
            dept, _ = Department.objects.get_or_create(title=title)
            dept_map[title] = dept
        self.stdout.write(f'  ✓ {len(dept_map)} 个部门')

        # 4. 创建超级管理员
        self.stdout.write('创建用户...')
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'is_superuser': True,
                'is_staff': True,
                'role': role_map['超级管理员'],
                'phone': '13800000000',
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(f'  ✓ 超级管理员 admin / admin123')
        else:
            self.stdout.write(f'  · 超级管理员已存在')

        # 5. 创建演示员工 + 普通账号
        if UserInfo.objects.count() == 0:
            self.stdout.write('创建演示员工...')
            demo_employees = [
                ('张三', 28, '技术部', '13911112222'),
                ('李四', 32, '技术部', '13922223333'),
                ('王五', 25, '产品部', '13933334444'),
                ('赵六', 30, '市场部', '13944445555'),
                ('孙七', 27, '人事部', '13955556666'),
                ('周八', 35, '财务部', '13966667777'),
            ]
            for name, age, dept, mobile in demo_employees:
                emp = UserInfo.objects.create(
                    name=name, age=age, mobile=mobile,
                    account='100000', create_time=date(2023, 6, 1),
                    gender=1, depart=dept_map[dept],
                )
            self.stdout.write(f'  ✓ {len(demo_employees)} 个演示员工')

        # 6. 创建演示考勤（最近7天）
        if Attendance.objects.count() == 0 and UserInfo.objects.count() > 0:
            self.stdout.write('创建演示考勤...')
            from datetime import time as dtime
            import random
            today = date.today()
            for emp in UserInfo.objects.all()[:5]:
                for i in range(7):
                    d = today - timedelta(days=i)
                    if random.random() > 0.1:   # 90% 正常
                        Attendance.objects.create(
                            employee=emp, date=d,
                            morning_time=dtime(9, random.randint(-1, 5) if False else 0),
                            evening_time=dtime(18, random.randint(0, 30)),
                        )
            self.stdout.write(f'  ✓ 演示考勤记录')

        # 7. 创建演示薪资（近6个月）
        if Salary.objects.count() == 0 and UserInfo.objects.count() > 0:
            self.stdout.write('创建演示薪资...')
            today = date.today()
            for emp in UserInfo.objects.all():
                for i in range(6):
                    month = f"{today.year}-{today.month - i:02d}" if today.month > i else f"{today.year-1}-{12 - (i-today.month):02d}"
                    month = today.replace(day=1) - timedelta(days=30*i)
                    month_str = month.strftime('%Y-%m')
                    Salary.objects.create(
                        employee=emp, month=month_str,
                        base_salary=8000 + emp.age * 100,
                        bonus=random.choice([500, 1000, 1500, 2000]),
                        deduction=random.choice([0, 100, 200]),
                    )
            self.stdout.write(f'  ✓ 演示薪资记录')

        # 8. 创建演示公告
        if Notice.objects.count() == 0:
            self.stdout.write('创建演示公告...')
            Notice.objects.create(
                title='系统上线公告',
                content='企业员工管理系统正式上线，欢迎大家使用！',
                author=admin_user, is_top=True,
            )
            Notice.objects.create(
                title='关于考勤打卡的通知',
                content='请大家每日按时打卡上班，打卡时间最晚不得超过 9:00。',
                author=admin_user,
            )
            self.stdout.write(f'  ✓ 演示公告')

        # 9. 创建演示任务
        if Task.objects.count() == 0 and UserInfo.objects.count() > 0:
            self.stdout.write('创建演示任务...')
            import random
            employees = list(UserInfo.objects.all())
            Task.objects.create(
                level='P0', title='修复登录验证码刷新问题',
                detail='部分浏览器下点击验证码图片不生效，排查浏览器缓存问题',
                owner=employees[0], status='doing',
            )
            Task.objects.create(
                level='P1', title='完成本月考勤统计',
                detail='输出 10 月份考勤报告，提交给人事部',
                owner=employees[1], status='pending',
            )
            Task.objects.create(
                level='P2', title='员工入职培训 PPT',
                detail='准备新员工入职培训资料，11月10日前完成',
                owner=employees[2], status='pending',
            )
            self.stdout.write(f'  ✓ 演示任务')

        self.stdout.write(self.style.SUCCESS('''
═══════════════════════════════════════
  ✓ 初始化完成！
  
  登录账号：
    admin / admin123    (超级管理员)
═══════════════════════════════════════
'''))
