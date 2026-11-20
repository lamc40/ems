""" Bootstrap 表单美化：ModelForm 基类，统一处理字段样式，避免每个 Form 重复写 __init__ 循环 """
from django import forms


class BootStrapModelForm(forms.ModelForm):
    """ 所有 ModelForm 继承此类，即可自动获得 Bootstrap 样式 """

    bootstrap_exclude_fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 循环找到所有的插件，添加 class="form-control"
        for name, field in self.fields.items():
            if name in self.bootstrap_exclude_fields:
                continue
            # 入职时间保留日期选择器
            if name == "create_time":
                field.widget.attrs = {"class": "form-control", "type": "date"}
            else:
                field.widget.attrs = {"class": "form-control", "placeholder": field.label}


class BootStrapForm(forms.Form):
    """ 普通 Form 基类，同样支持 bootstrap_exclude_fields """

    bootstrap_exclude_fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            if name in self.bootstrap_exclude_fields:
                continue
            if field.widget.attrs:
                field.widget.attrs["class"] = "form-control"
                field.widget.attrs["placeholder"] = field.label
            else:
                field.widget.attrs = {
                    "class": "form-control",
                    "placeholder": field.label,
                }
