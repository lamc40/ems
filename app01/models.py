""" 模型层：企业员工管理系统全部数据模型

变化说明（对照旧版）：
1. 新增 User(AbstractUser) —— 自定义用户模型，替代旧 Admin 表作为登录主体
2. 新增 Role / Permission —— RBAC 权限体系
3. UserInfo 增加 mobile（手机号）、avatar（头像）字段
4. 新增 Attendance —— 考勤管理（状态由上下班时间自动计算）
5. 新增 Salary —— 薪资管理（实发 = 基本工资 + 奖金 - 扣款）
6. 新增 Notice —— 公告管理（置顶、发布时间 auto_now_add）
7. Admin 保留但标记废弃，数据迁移脚本会迁移到 User
"""
import os

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


# ==================== 用户 & RBAC ====================

class Role(models.Model):
    """ 角色表：超级管理员 / 部门管理员 / 普通员工 """
    name = models.CharField("角色名", max_length=32, unique=True)
    code = models.CharField("角色编码", max_length=32, unique=True)
    description = models.CharField("描述", max_length=200, blank=True)
    permissions = models.ManyToManyField('Permission', blank=True, verbose_name="权限")

    class Meta:
        verbose_name = "角色"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Permission(models.Model):
    """ 权限表：每个权限对应一个接口/操作 """
    code = models.CharField("权限编码", max_length=64, unique=True)   # 如 'depart.view'
    name = models.CharField("权限名", max_length=64)                  # 如 '查看部门'
    module = models.CharField("所属模块", max_length=32)              # 如 '部门管理'

    class Meta:
        verbose_name = "权限"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"[{self.module}] {self.name}"


class User(AbstractUser):
    """ 自定义用户模型：继承 Django AbstractUser，扩展 RBAC

    字段说明：
    - username / password / email 等由 AbstractUser 提供
    - role：外键关联角色（一个用户一个角色）
    - phone：联系电话（可选，区别于员工表的手机号）
    """
    role = models.ForeignKey(
        Role, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="角色"
    )
    phone = models.CharField("联系电话", max_length=20, blank=True)
    depart = models.ForeignKey(
        'Department', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="所属部门"
    )

    class Meta:
        verbose_name = "系统用户"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.username

    def has_perm_code(self, code):
        """ 便捷方法：判断当前用户是否拥有某权限编码 """
        if self.is_superuser:
            return True
        if not self.role:
            return False
        return self.role.permissions.filter(code=code).exists()


# ==================== 部门 & 员工 ====================

class Department(models.Model):
    """ 部门表 """
    title = models.CharField(verbose_name='部门名称', max_length=32)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="部门负责人"
    )

    class Meta:
        verbose_name = "部门"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title


def avatar_upload_path(instance, filename):
    """ 员工头像上传路径：media/avatars/<员工id>_<文件名> """
    ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'png'
    return f'avatars/{instance.id}_{instance.name}.{ext}'


class UserInfo(models.Model):
    """ 员工档案表：员工详细业务信息（区别于 User 的认证信息） """
    name = models.CharField("姓名", max_length=32)
    age = models.IntegerField("年龄", default=2)
    account = models.CharField("账户余额", max_length=16, default="100000")
    create_time = models.DateField("入职时间")
    mobile = models.CharField("手机号", max_length=11, blank=True, null=True)
    avatar = models.ImageField("头像", upload_to=avatar_upload_path, blank=True, null=True)
    # 性别
    gender_choices = ((1, "男"), (2, "女"))
    gender = models.SmallIntegerField("性别", choices=gender_choices, null=True, blank=True)
    # 外键：部门
    depart = models.ForeignKey(
        Department, on_delete=models.CASCADE, null=True, blank=True,
        verbose_name="部门", related_name="employees"
    )
    # 关联系统用户（可选，登录用户对应的员工档案）
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="登录账号"
    )

    class Meta:
        verbose_name = "员工"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


# ==================== 考勤管理 ====================

class Attendance(models.Model):
    """ 考勤记录：状态由上下班时间自动计算

    状态规则：
    - 上班时间 > 09:00 → 迟到
    - 下班时间 < 18:00 → 早退
    - 无上下班记录 → 缺勤
    - 其余 → 正常
    """
    STATUS_CHOICES = (
        ('normal', '正常'),
        ('late', '迟到'),
        ('early', '早退'),
        ('late_early', '迟到+早退'),
        ('absent', '缺勤'),
    )
    WORK_START = '09:00'   # 上班标准时间
    WORK_END = '18:00'     # 下班标准时间

    employee = models.ForeignKey(UserInfo, on_delete=models.CASCADE, verbose_name="员工")
    date = models.DateField("日期")
    morning_time = models.TimeField("上班打卡时间", null=True, blank=True)
    evening_time = models.TimeField("下班打卡时间", null=True, blank=True)
    status = models.CharField("考勤状态", max_length=16, choices=STATUS_CHOICES, default='normal')
    remark = models.CharField("备注", max_length=200, blank=True)

    class Meta:
        verbose_name = "考勤"
        verbose_name_plural = verbose_name
        unique_together = [('employee', 'date')]   # 同一员工同一天只有一条记录
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee.name} - {self.date}"

    def calculate_status(self):
        """ 根据上下班时间自动计算考勤状态并保存

        返回计算后的状态字符串（也会写入 self.status 并 save）
        """
        from datetime import datetime, time

        if not self.morning_time and not self.evening_time:
            self.status = 'absent'
        else:
            late = False
            early = False
            work_start = time(9, 0)
            work_end = time(18, 0)

            if self.morning_time and self.morning_time > work_start:
                late = True
            if self.evening_time and self.evening_time < work_end:
                early = True

            if late and early:
                self.status = 'late_early'
            elif late:
                self.status = 'late'
            elif early:
                self.status = 'early'
            else:
                self.status = 'normal'

        self.save(update_fields=['status'])
        return self.status


# ==================== 薪资管理 ====================

class Salary(models.Model):
    """ 薪资记录：实发 = 基本工资 + 奖金 - 扣款

    total 字段由 save() 自动计算，无需前端传入。
    """
    employee = models.ForeignKey(UserInfo, on_delete=models.CASCADE, verbose_name="员工")
    month = models.CharField("月份", max_length=7)   # 格式 YYYY-MM
    base_salary = models.DecimalField("基本工资", max_digits=10, decimal_places=2, default=0)
    bonus = models.DecimalField("奖金", max_digits=10, decimal_places=2, default=0)
    deduction = models.DecimalField("扣款", max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField("实发工资", max_digits=10, decimal_places=2, default=0)
    remark = models.CharField("备注", max_length=200, blank=True)

    class Meta:
        verbose_name = "薪资"
        verbose_name_plural = verbose_name
        unique_together = [('employee', 'month')]   # 同一员工同一月份只有一条记录
        ordering = ['-month']

    def __str__(self):
        return f"{self.employee.name} - {self.month} - {self.total}"

    def save(self, *args, **kwargs):
        """ 重写 save：自动计算实发工资 """
        self.total = (self.base_salary or 0) + (self.bonus or 0) - (self.deduction or 0)
        super().save(*args, **kwargs)


# ==================== 公告管理 ====================

class Notice(models.Model):
    """ 公告：可置顶、按时间排序、支持搜索 """
    title = models.CharField("标题", max_length=200)
    content = models.TextField("内容")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name="发布人"
    )
    created_at = models.DateTimeField("发布时间", auto_now_add=True)
    is_top = models.BooleanField("是否置顶", default=False)

    class Meta:
        verbose_name = "公告"
        verbose_name_plural = verbose_name
        ordering = ['-is_top', '-created_at']   # 置顶优先，然后按时间倒序

    def __str__(self):
        return self.title


# ==================== 任务管理 ====================

class Task(models.Model):
    """ 任务表（T9 任务管理 - AJAX）

    级别 choices：P0 紧急 / P1 高 / P2 中 / P3 低
    状态 choices：待办 / 进行中 / 已完成
    """
    LEVEL_CHOICES = (
        ('P0', '紧急'),
        ('P1', '高'),
        ('P2', '中'),
        ('P3', '低'),
    )
    STATUS_CHOICES = (
        ('pending', '待办'),
        ('doing', '进行中'),
        ('done', '已完成'),
    )

    level = models.CharField("级别", max_length=4, choices=LEVEL_CHOICES, default='P2')
    title = models.CharField("标题", max_length=100)
    detail = models.TextField("详情", blank=True)
    owner = models.ForeignKey(
        UserInfo, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="负责人"
    )
    status = models.CharField("状态", max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "任务"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.level}] {self.title}"


# ==================== 靓号（旧模块保留） ====================

class PrettyNum(models.Model):
    """ 靓号表（原课程示例，保留做演示用） """
    mobile = models.CharField(verbose_name="手机号", max_length=11)
    price = models.IntegerField(verbose_name="价格", default=0)
    level_choices = ((1, "1级"), (2, "2级"), (3, "3级"), (4, "4级"))
    level = models.SmallIntegerField(verbose_name="级别", choices=level_choices, default=1)
    status_choices = ((1, "已占用"), (2, "未使用"))
    status = models.SmallIntegerField(verbose_name="状态", choices=status_choices, default=2)

    def __str__(self):
        return self.mobile


# ==================== AI 智能助手 ====================

class Knowledge(models.Model):
    """ 企业知识库（制度/手册条目），供智能问答检索。

    T3 任务书：SQL 关键词检索 → 拼入提示词 → 让大模型"照着资料回答"。
    参考代码版：只保留 title + content 两个核心字段。
    """
    title = models.CharField(verbose_name="标题", max_length=128)
    content = models.TextField(verbose_name="内容")

    class Meta:
        verbose_name = "知识库条目"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title


class ChatHistory(models.Model):
    """ 多轮对话历史（T5 选做）

    存 session_key（Django session_key 或前端自定义）+ role + content。
    """
    session_key = models.CharField("会话标识", max_length=64, db_index=True)
    role = models.CharField("角色", max_length=12)   # system / user / assistant
    content = models.TextField("内容")
    created_at = models.DateTimeField("时间", auto_now_add=True)

    class Meta:
        verbose_name = "对话历史"
        verbose_name_plural = verbose_name
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.session_key[:8]}] {self.role}: {self.content[:20]}"


# ==================== 梗识别知识库 ====================

class Meme(models.Model):
    """ 网络梗知识库 —— 用于 AI 识别并解释用户输入中的梗

    字段说明：
    - name: 梗名称（如 "打工人"）
    - keywords: 触发关键词（逗号分隔，如 "打工人,打工魂"）
    - explanation: 梗的详细解释
    - origin: 梗的来源/出处（可选）
    - category: 梗分类（网络流行语 / 职场梗 / 电竞梗 等）
    - is_active: 是否启用
    """
    CATEGORY_CHOICES = (
        ('internet', '网络流行语'),
        ('workplace', '职场梗'),
        ('gaming', '电竞/游戏梗'),
        ('variety', '综艺梗'),
        ('anime', '动漫梗'),
        ('other', '其他'),
    )

    name = models.CharField("梗名称", max_length=64)
    keywords = models.CharField("触发关键词", max_length=255,
                                help_text="多个关键词用英文逗号分隔")
    explanation = models.TextField("梗解释")
    origin = models.CharField("来源出处", max_length=200, blank=True)
    category = models.CharField("分类", max_length=16, choices=CATEGORY_CHOICES,
                                default='internet')
    is_active = models.BooleanField("启用", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "网络梗"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_keyword_list(self):
        """ 返回关键词列表（用于匹配）"""
        return [k.strip() for k in self.keywords.split(',') if k.strip()]


# ==================== 旧 Admin 模型（已废弃，保留兼容迁移） ====================

class Admin(models.Model):
    """ 旧管理员表 —— 已被 User(AbstractUser) 替代，保留是为了不破坏旧迁移链 """
    username = models.CharField(verbose_name="用户名", max_length=32)
    password = models.CharField(verbose_name="密码", max_length=64)

    class Meta:
        verbose_name = "旧管理员（已废弃）"

    def __str__(self):
        return self.username


# ==================== 第 18-21 章教程新增模型 ====================

class Order(models.Model):
    """ 订单（教程 18 章）"""
    oid = models.CharField(verbose_name="订单号", max_length=64)
    title = models.CharField(verbose_name="名称", max_length=32)
    price = models.IntegerField(verbose_name="价格")

    status_choices = (
        (1, "待支付"),
        (2, "已支付"),
    )
    status = models.SmallIntegerField(verbose_name="状态", choices=status_choices, default=1)
    admin = models.ForeignKey(verbose_name="管理员", to=User, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "订单"


class Boss(models.Model):
    """ 老板（教程 20 章，Form 上传示例）"""
    name = models.CharField(verbose_name="姓名", max_length=32)
    age = models.IntegerField(verbose_name="年龄")
    img = models.CharField(verbose_name="头像", max_length=128)

    class Meta:
        verbose_name = "老板"


class City(models.Model):
    """ 城市（教程 20-21 章，ModelForm + FileField 示例）"""
    name = models.CharField(verbose_name="名称", max_length=32)
    count = models.IntegerField(verbose_name="人口")
    img = models.FileField(verbose_name="Logo", max_length=128, upload_to='city/')

    class Meta:
        verbose_name = "城市"


class XX(models.Model):
    """ 头像预览示例（教程 20.4 章）"""
    title = models.CharField(verbose_name="名称", max_length=32)
    image = models.FileField(verbose_name="头像", upload_to="avatar/")

    class Meta:
        verbose_name = "头像示例"
