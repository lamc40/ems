""" 表单定义（ModelForm）：与模型绑定，负责表单字段生成、数据校验和保存

样式统一由 utils/bootstrap.py 的 BootStrapModelForm 基类处理，
本文件只关注字段定义和校验规则。

密码安全：使用 Django 内置 make_password/check_password（PBKDF2 算法），
严禁明文或裸 MD5 存储（对照任务书 T4 技术规范）。
"""
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator

from app01 import models
from app01.utils.bootstrap import BootStrapModelForm

User = get_user_model()


# ==================== 管理员（系统用户）表单 ====================

class AdminModelForm(BootStrapModelForm):
    """ 新建管理员用的 ModelForm

    - 动态增加 confirm_password 字段（不在 model 中，仅用于校验）
    - password 字段用 PasswordInput widget（页面显示 *** 而非明文）
    - save 时对 password 做 Django make_password 加密后再存入数据库
    """
    confirm_password = forms.CharField(
        label="确认密码",
        widget=forms.PasswordInput(render_value=True),
    )

    class Meta:
        model = User
        fields = ["username", "password", "role", "phone", "depart"]
        widgets = {
            "password": forms.PasswordInput(render_value=True),
        }

    def clean_username(self):
        """ 字段级校验：用户名唯一 """
        txt = self.cleaned_data["username"]
        if User.objects.filter(username=txt).exists():
            raise forms.ValidationError("用户名已存在")
        return txt

    def clean(self):
        """ 整体校验：两次密码是否一致 """
        cleaned_data = super().clean()
        pwd = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")
        if pwd and confirm and pwd != confirm:
            self.add_error("confirm_password", "两次输入的密码不一致")
        return cleaned_data

    def save(self, commit=True):
        """ 重写 save：password 用 make_password 加密后再保存

        Django 的 set_password 方法等同于 make_password + save
        """
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])   # PBKDF2 安全哈希
        user.is_staff = True                                # 管理员标记
        if commit:
            user.save()
        return user


class AdminEditModelForm(BootStrapModelForm):
    """ 编辑管理员：只允许修改用户名、角色、手机号、部门，不展示密码 """

    class Meta:
        model = User
        fields = ["username", "role", "phone", "depart"]

    def clean_username(self):
        """ 字段级校验：用户名唯一（编辑时排除当前行自身） """
        txt = self.cleaned_data["username"]
        if User.objects.exclude(id=self.instance.pk).filter(username=txt).exists():
            raise forms.ValidationError("用户名已存在")
        return txt


class AdminResetModelForm(BootStrapModelForm):
    """ 重置密码：新密码 + 确认密码，save 时用 set_password 加密 """
    password = forms.CharField(
        label="新密码",
        widget=forms.PasswordInput(render_value=True),
    )
    confirm_password = forms.CharField(
        label="确认密码",
        widget=forms.PasswordInput(render_value=True),
    )

    class Meta:
        model = User
        fields = []   # 纯动态表单，无 model 字段

    def clean_password(self):
        """ 字段级校验：新密码不能与原密码相同 """
        new_pwd = self.cleaned_data["password"]
        if check_password(new_pwd, self.instance.password):
            raise forms.ValidationError("不能与以前的密码相同")
        return new_pwd

    def clean(self):
        """ 整体校验：两次密码是否一致 """
        cleaned_data = super().clean()
        pwd = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")
        if pwd and confirm and pwd != confirm:
            self.add_error("confirm_password", "密码不一致")
        return cleaned_data

    def save(self, commit=True):
        """ 重写 save：对新密码 set_password 加密后更新 """
        self.instance.set_password(self.cleaned_data["password"])
        if commit:
            self.instance.save()
        return self.instance


# ==================== 员工表单 ====================

class UserModelForm(BootStrapModelForm):
    """ 新建员工用的 ModelForm

    手机号校验：正则 ^1[3-9]\\d{9}$（任务书 T3 要求）
    """
    name = forms.CharField(min_length=2, label="姓名")
    mobile = forms.CharField(
        label="手机号",
        required=False,
        validators=[
            RegexValidator(r'^1[3-9]\d{9}$', '手机号格式错误，需为1开头的11位数字'),
        ],
    )

    class Meta:
        model = models.UserInfo
        fields = ["name", "age", "mobile", "account", "create_time", "gender", "depart", "avatar"]
        widgets = {
            "create_time": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_age(self):
        """ 字段级校验：年龄范围 16-80 """
        age = self.cleaned_data["age"]
        if age < 16 or age > 80:
            raise forms.ValidationError("年龄应在 16-80 之间")
        return age

    def clean_mobile(self):
        """ 字段级校验：手机号唯一（新建时全表查重） """
        mobile = self.cleaned_data.get("mobile")
        if mobile and models.UserInfo.objects.filter(mobile=mobile).exists():
            raise forms.ValidationError("手机号已被使用")
        return mobile


class UserEditModelForm(BootStrapModelForm):
    """ 编辑员工：手机号唯一性校验需排除自身 """
    name = forms.CharField(min_length=2, label="姓名")
    mobile = forms.CharField(
        label="手机号",
        required=False,
        validators=[
            RegexValidator(r'^1[3-9]\d{9}$', '手机号格式错误，需为1开头的11位数字'),
        ],
    )

    class Meta:
        model = models.UserInfo
        fields = ["name", "age", "mobile", "account", "create_time", "gender", "depart", "avatar"]
        widgets = {
            "create_time": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_age(self):
        age = self.cleaned_data["age"]
        if age < 16 or age > 80:
            raise forms.ValidationError("年龄应在 16-80 之间")
        return age

    def clean_mobile(self):
        mobile = self.cleaned_data.get("mobile")
        if mobile and models.UserInfo.objects.exclude(id=self.instance.pk).filter(mobile=mobile).exists():
            raise forms.ValidationError("手机号已被使用")
        return mobile


# ==================== 靓号表单 ====================

class PrettyModelForm(BootStrapModelForm):
    """ 新建靓号：手机号正则 + 唯一性校验 """
    mobile = forms.CharField(
        label="手机号",
        validators=[
            RegexValidator(r'^1\d{10}$', '手机号格式错误，需为1开头的11位数字'),
        ],
    )

    class Meta:
        model = models.PrettyNum
        fields = ["mobile", "price", "level", "status"]

    def clean_mobile(self):
        txt_mobile = self.cleaned_data["mobile"]
        if models.PrettyNum.objects.filter(mobile=txt_mobile).exists():
            raise forms.ValidationError("手机号已存在")
        return txt_mobile


class PrettyEditModelForm(BootStrapModelForm):
    """ 编辑靓号：唯一性校验需排除自身 """
    mobile = forms.CharField(
        label="手机号",
        validators=[
            RegexValidator(r'^1\d{10}$', '手机号格式错误，需为1开头的11位数字'),
        ],
    )

    class Meta:
        model = models.PrettyNum
        fields = ["mobile", "price", "level", "status"]

    def clean_mobile(self):
        txt_mobile = self.cleaned_data["mobile"]
        if models.PrettyNum.objects.exclude(id=self.instance.pk).filter(mobile=txt_mobile).exists():
            raise forms.ValidationError("手机号已存在")
        return txt_mobile
