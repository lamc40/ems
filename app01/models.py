""" 模型层：定义数据库表结构，每个类对应一张MySQL表（表名自动生成：app01_department等） """
from django.db import models


class Department(models.Model):
    """ 部门表 """
    title = models.CharField(verbose_name='标题', max_length=32)   # 部门名称

    def __str__(self):
        """ 返回部门名称：员工表外键下拉框、admin后台显示时用 """
        return self.title


class UserInfo(models.Model):
    """ 员工表 """
    name = models.CharField(max_length=32)                      # 姓名
    password = models.CharField(max_length=64)                  # 密码
    age = models.IntegerField(default=2)                        # 年龄
    account = models.CharField(max_length=16, default="100000") # 账户余额
    create_time = models.DateField()                            # 入职时间
    # 外键：关联部门表，数据库列名 depart_id 对应 Department 的 id
    # on_delete=CASCADE：删除部门时级联删除该部门下的员工
    depart = models.ForeignKey(
        verbose_name="部门",
        to="Department",
        to_field="id",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_column="depart_id",
    )
    # 性别选项：数据库存数字1/2，页面用 get_gender_display 显示"男/女"
    gender_choices = (
        (1, "男"),
        (2, "女"),
    )
    gender = models.SmallIntegerField(choices=gender_choices, null=True, blank=True)


class PrettyNum(models.Model):
    """ 靓号表 """
    mobile = models.CharField(verbose_name="手机号", max_length=11)   # 手机号（11位字符串，不能用整型，避免首位0丢失/溢出）
    price = models.IntegerField(verbose_name="价格", default=0)       # 靓号价格，默认0
    # 级别选项：数据库存数字，页面显示中文（模板中用 get_level_display）
    level_choices = (
        (1, "1级"),
        (2, "2级"),
        (3, "3级"),
        (4, "4级"),
    )
    level = models.SmallIntegerField(verbose_name="级别", choices=level_choices, default=1)   # 靓号级别，默认1级
    # 状态选项：数据库存数字，页面显示中文（模板中用 get_status_display）
    status_choices = (
        (1, "已占用"),
        (2, "未使用"),
    )
    status = models.SmallIntegerField(verbose_name="状态", choices=status_choices, default=2)  # 使用状态，默认未使用
