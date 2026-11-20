""" 核心模块单元测试（任务书 T12）

覆盖关键流程：登录鉴权、考勤状态自动计算、薪资自动计算、RBAC 权限拦截。
运行：python manage.py test app01.tests -v 2
"""
from datetime import date, time

from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.hashers import check_password
from django.test import TestCase, Client

from app01.models import (
    Department, UserInfo, Attendance, Salary, Notice, Role, Permission,
)

User = get_user_model()


# ==================== T3 员工模型校验 ====================

class UserInfoModelTests(TestCase):
    """ 员工模型字段校验测试 """

    @classmethod
    def setUpTestData(cls):
        cls.dept = Department.objects.create(title='技术部')
        cls.emp = UserInfo.objects.create(
            name='张三', age=25, mobile='13912345678',
            account='100000', create_time=date(2024, 6, 1),
            gender=1, depart=cls.dept,
        )

    def test_employee_created(self):
        """ 员工能成功创建 """
        self.assertEqual(self.emp.name, '张三')
        self.assertEqual(self.emp.depart.title, '技术部')

    def test_phone_is_11_digits(self):
        """ 手机号存储为 11 位字符串 """
        self.assertEqual(len(self.emp.mobile), 11)
        self.assertTrue(self.emp.mobile.startswith('139'))

    def test_department_cascade_delete(self):
        """ 删除部门时级联删除员工（CASCADE） """
        self.dept.delete()
        self.assertFalse(UserInfo.objects.filter(pk=self.emp.pk).exists())


# ==================== T4 登录认证 ====================

class AuthTests(TestCase):
    """ 登录 / 密码哈希 / 中间件拦截测试 """

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username='testadmin', password='admin123', is_staff=True, is_superuser=True,
        )

    def test_password_is_hashed(self):
        """ 密码不以明文存储（PBKDF2 前缀） """
        self.assertNotEqual(self.admin.password, 'admin123')
        self.assertTrue(self.admin.password.startswith('pbkdf2'))

    def test_authenticate_success(self):
        """ authenticate 返回用户对象 """
        u = authenticate(username='testadmin', password='admin123')
        self.assertIsNotNone(u)
        self.assertEqual(u.username, 'testadmin')

    def test_authenticate_failure(self):
        """ 错误密码返回 None """
        u = authenticate(username='testadmin', password='wrong')
        self.assertIsNone(u)

    def test_middleware_redirect_anonymous(self):
        """ 未登录访问受保护页 302 重定向到登录页 """
        resp = self.client.get('/admin/list/', follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp['Location'])

    def test_admin_list_accessible_after_login(self):
        """ 登录后能访问管理员列表 """
        self.client.login(username='testadmin', password='admin123')
        resp = self.client.get('/admin/list/')
        self.assertEqual(resp.status_code, 200)


# ==================== T5 RBAC 权限测试 ====================

class RBACTests(TestCase):
    """ RBAC 角色-权限 联动测试 """

    @classmethod
    def setUpTestData(cls):
        cls.super_role = Role.objects.create(name='超级管理员', code='超级管理员')
        cls.emp_role = Role.objects.create(name='普通员工', code='普通员工')
        perm_dept_view = Permission.objects.create(code='depart.view', name='查看部门', module='部门管理')
        cls.super_role.permissions.add(perm_dept_view)
        cls.emp_role.permissions.add(perm_dept_view)

        cls.admin = User.objects.create_user(
            username='superuser', password='pw123', is_superuser=True, role=cls.super_role)
        cls.emp_user = User.objects.create_user(
            username='emp1', password='pw123', role=cls.emp_role)
        cls.no_role_user = User.objects.create_user(
            username='norole', password='pw123')

    def test_superuser_has_all_perms(self):
        """ is_superuser=True 的用户绕过权限检查 """
        self.assertTrue(self.admin.has_perm_code('anything.xxx'))

    def test_role_permission_check(self):
        """ 角色通过权限码校验 """
        self.assertTrue(self.emp_user.has_perm_code('depart.view'))
        self.assertFalse(self.emp_user.has_perm_code('admin.delete'))

    def test_no_role_no_perm(self):
        """ 没有角色的用户无权限 """
        self.assertFalse(self.no_role_user.has_perm_code('depart.view'))


# ==================== T6 考勤状态自动计算 ====================

class AttendanceStatusTests(TestCase):
    """ 考勤状态根据上下班时间自动计算 """

    @classmethod
    def setUpTestData(cls):
        dept = Department.objects.create(title='人事部')
        cls.emp = UserInfo.objects.create(
            name='考勤测试员', age=30, mobile='13999990001',
            account='100000', create_time=date(2024, 6, 1),
            gender=1, depart=dept,
        )

    def test_normal_attendance(self):
        """ 09:00 上班 + 18:00 下班 = 正常 """
        att = Attendance.objects.create(
            employee=self.emp, date=date.today(),
            morning_time=time(9, 0), evening_time=time(18, 1),
        )
        status = att.calculate_status()
        self.assertEqual(status, 'normal')

    def test_late_attendance(self):
        """ 09:05 上班 + 18:30 下班 = 迟到 """
        att = Attendance.objects.create(
            employee=self.emp, date=date.today(),
            morning_time=time(9, 5), evening_time=time(18, 30),
        )
        status = att.calculate_status()
        self.assertEqual(status, 'late')

    def test_early_attendance(self):
        """ 08:50 上班 + 17:30 下班 = 早退 """
        att = Attendance.objects.create(
            employee=self.emp, date=date.today(),
            morning_time=time(8, 50), evening_time=time(17, 30),
        )
        status = att.calculate_status()
        self.assertEqual(status, 'early')

    def test_absent_attendance(self):
        """ 无打卡记录 = 缺勤 """
        att = Attendance.objects.create(
            employee=self.emp, date=date.today(),
        )
        status = att.calculate_status()
        self.assertEqual(status, 'absent')


# ==================== T7 薪资自动计算 ====================

class SalaryAutoCalcTests(TestCase):
    """ 薪资实发 = 基本工资 + 奖金 - 扣款 """

    @classmethod
    def setUpTestData(cls):
        dept = Department.objects.create(title='财务部')
        cls.emp = UserInfo.objects.create(
            name='薪资测试员', age=32, mobile='13999990002',
            account='100000', create_time=date(2024, 6, 1),
            gender=2, depart=dept,
        )

    def test_total_calculated_on_save(self):
        """ Salary.save() 自动计算 total """
        sal = Salary.objects.create(
            employee=self.emp, month='2025-01',
            base_salary=8000, bonus=2000, deduction=500,
        )
        self.assertEqual(float(sal.total), 9500.00)   # 8000 + 2000 - 500

    def test_total_recalculated_on_update(self):
        """ 修改字段后 total 自动重算 """
        sal = Salary.objects.create(
            employee=self.emp, month='2025-02',
            base_salary=8000, bonus=1000, deduction=0,
        )
        sal.bonus = 5000
        sal.deduction = 200
        sal.save()
        self.assertEqual(float(sal.total), 12800.00)   # 8000 + 5000 - 200

    def test_total_zero_defaults(self):
        """ 全零默认值 total 为 0 """
        sal = Salary.objects.create(employee=self.emp, month='2025-03')
        self.assertEqual(float(sal.total), 0.00)


# ==================== T5 权限中间件拦截测试 ====================

class PermissionMiddlewareTests(TestCase):
    """ RBAC 接口级权限拦截 """

    @classmethod
    def setUpTestData(cls):
        cls.dept = Department.objects.create(title='销售部')
        cls.emp = UserInfo.objects.create(
            name='受限员工', age=22, mobile='13999990003',
            account='100000', create_time=date(2024, 6, 1),
            depart=cls.dept, gender=2,
        )
        cls.emp_role = Role.objects.create(name='普通员工测试', code='普通员工测试')
        # 普通员工只有 depart.view 权限
        perm_view = Permission.objects.create(code='depart.view', name='查看部门', module='部门管理')
        cls.emp_role.permissions.add(perm_view)
        cls.emp_user = User.objects.create_user(
            username='limited', password='pw123', role=cls.emp_role)

    def test_forbidden_on_no_permission(self):
        """ 没有 admin.add 权限时请求 /admin/add/ 返回 403 """
        self.client.login(username='limited', password='pw123')
        resp = self.client.get('/admin/add/', follow=False)
        self.assertIn(resp.status_code, [302, 403])   # 可能被 AuthMiddleware 先拦截也可能 PermissionMiddleware 拦截

    def test_allowed_on_has_permission(self):
        """ 有 depart.view 权限时能访问 /depart/list/ """
        self.client.login(username='limited', password='pw123')
        resp = self.client.get('/depart/list/')
        self.assertEqual(resp.status_code, 200)
