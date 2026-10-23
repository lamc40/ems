""" 表单层（ModelForm）：与模型绑定，负责表单字段生成、数据校验和保存 """
from django import forms
from django.core.validators import RegexValidator

from app01 import models


class UserModelForm(forms.ModelForm):
    """ 新建用户用的ModelForm """
    # fields = ["name"...]只能判断是否为空，如果有其他的判断验证条件需要单独写
    name = forms.CharField(min_length=3, label="用户名")
    # password = forms.CharField(label="用户名", validators=正则表达式)

    class Meta:
        model = models.UserInfo
        # fields会生成输入框，gender会自动获取字段变成下拉框，depart而不是depart_
        # 但是这里depart获取的是对象，例如我们之前输出的类型，要有具体的值需要在model中写__str__
        fields = ["name", "password", "age", "account", "create_time", "gender", "depart"]
        # widgets对应原来 <input type="text" class="form-control" placeholder="女"> 中的样式
        widgets = {
            "create_time": forms.DateInput(attrs={"type": "date"}),
        }

    # 根据底层类源码重新定义一个方法
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 循环找到所有的插件，添加了class="form-control"
        for name, field in self.fields.items():
            # 如果其中某个字段不加
            # if name == "password":
            #     continue

            # placeholder="姓名" 样式也可以加
            # 入职时间保留日期选择器
            if name == "create_time":
                field.widget.attrs = {"class": "form-control", "type": "date"}
            else:
                field.widget.attrs = {"class": "form-control", "placeholder": field.label}


class PrettyModelForm(forms.ModelForm):
    """ 新建靓号用的ModelForm """
    # 手机号校验：用正则限制为1开头的11位数字，格式不符时提示错误信息
    mobile = forms.CharField(
        label="手机号",
        validators=[
            RegexValidator(r'^1\d{10}$', '手机号格式错误，需为1开头的11位数字'),
        ],
    )

    class Meta:
        model = models.PrettyNum
        # 表单只展示这四个字段，level/status 会自动渲染成下拉框
        fields = ["mobile", "price", "level", "status"]

    def __init__(self, *args, **kwargs):
        """ 循环给所有字段添加 Bootstrap 样式和占位提示 """
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs = {"class": "form-control", "placeholder": field.label}

    def clean_mobile(self):
        """ 字段级校验钩子：校验手机号唯一（新建时，全表查重） """
        txt_mobile = self.cleaned_data["mobile"]  # 获取用户提交的、已通过格式校验的手机号
        exists = models.PrettyNum.objects.filter(mobile=txt_mobile).exists()  # 查库判断是否已存在
        if exists:
            raise forms.ValidationError("手机号已存在")  # 抛出校验错误，会显示在对应字段下方
        return txt_mobile  # 校验通过必须返回该字段的值，否则保存时为 None


class PrettyEditModelForm(forms.ModelForm):
    """ 编辑靓号用的ModelForm（唯一性校验需排除自身） """
    # 手机号校验：用正则限制为1开头的11位数字
    mobile = forms.CharField(
        label="手机号",
        validators=[
            RegexValidator(r'^1\d{10}$', '手机号格式错误，需为1开头的11位数字'),
        ],
    )

    class Meta:
        model = models.PrettyNum
        fields = ["mobile", "price", "level", "status"]

    def __init__(self, *args, **kwargs):
        """ 循环给所有字段添加 Bootstrap 样式和占位提示 """
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs = {"class": "form-control", "placeholder": field.label}

    def clean_mobile(self):
        """ 字段级校验钩子：校验手机号唯一（编辑时排除当前行自身，否则未修改手机号也会报错） """
        txt_mobile = self.cleaned_data["mobile"]
        # exclude(id=self.instance.pk)：排除正在编辑的这条记录后再查重
        exists = models.PrettyNum.objects.exclude(id=self.instance.pk).filter(mobile=txt_mobile).exists()
        if exists:
            raise forms.ValidationError("手机号已存在")
        return txt_mobile
