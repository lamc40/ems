""" Bootstrap 表单美化：ModelForm 基类，统一处理字段样式，避免每个 Form 重复写 __init__ 循环 """
from django import forms


class BootStrapModelForm(forms.ModelForm):
    """ 所有 ModelForm 继承此类，即可自动获得 Bootstrap 样式 """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 循环找到所有的插件，添加 class="form-control"
        for name, field in self.fields.items():
            # 入职时间保留日期选择器
            if name == "create_time":
                field.widget.attrs = {"class": "form-control", "type": "date"}
            else:
                # placeholder="姓名" 样式也可以加
                field.widget.attrs = {"class": "form-control", "placeholder": field.label}
