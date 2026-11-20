""" 文件上传（教程 20 章）—— 三种方式：原始/Form/ModelForm + 头像预览 """
import os

from django.conf import settings
from django import forms
from django.shortcuts import render, HttpResponse

from app01 import models
from app01.utils.bootstrap import BootStrapForm, BootStrapModelForm


def upload_list(request):
    """ 原始方式：request.FILES + chunks() 分块写盘 """
    if request.method == "GET":
        return render(request, 'upload_list.html')

    file_object = request.FILES.get("avatar")
    if not file_object:
        return HttpResponse("未选择文件")

    f = open(file_object.name, mode='wb')
    for chunk in file_object.chunks():
        f.write(chunk)
    f.close()

    return HttpResponse("上传成功")


# ========== 20.2 Form 上传（Boss 表） ==========

class UpForm(BootStrapForm):
    bootstrap_exclude_fields = ['img']

    name = forms.CharField(label="姓名")
    age = forms.IntegerField(label="年龄")
    img = forms.FileField(label="头像")


def upload_form(request):
    title = "Form上传"
    if request.method == "GET":
        form = UpForm()
        return render(request, 'upload_form.html', {"form": form, "title": title})

    form = UpForm(data=request.POST, files=request.FILES)
    if form.is_valid():
        image_object = form.cleaned_data.get("img")

        boss_dir = os.path.join(settings.MEDIA_ROOT, "boss")
        if not os.path.exists(boss_dir):
            os.makedirs(boss_dir)

        media_path = os.path.join(boss_dir, image_object.name)
        with open(media_path, mode='wb') as f:
            for chunk in image_object.chunks():
                f.write(chunk)

        models.Boss.objects.create(
            name=form.cleaned_data['name'],
            age=form.cleaned_data['age'],
            img="boss/" + image_object.name,
        )
        return HttpResponse("成功")
    return render(request, 'upload_form.html', {"form": form, "title": title})


# ========== 20.3 ModelForm 上传（City 表） ==========

class UpModelForm(BootStrapModelForm):
    bootstrap_exclude_fields = ['img']

    class Meta:
        model = models.City
        fields = "__all__"


def upload_modal_form(request):
    """ ModelForm 上传 —— 文件自动存到 upload_to 目录 """
    title = "ModelForm上传文件"
    if request.method == "GET":
        form = UpModelForm()
        return render(request, 'upload_form.html', {"form": form, 'title': title})

    form = UpModelForm(data=request.POST, files=request.FILES)
    if form.is_valid():
        form.save()
        return HttpResponse("成功")
    return render(request, 'upload_form.html', {"form": form, 'title': title})


# ========== 20.4 头像预览（XX 表） ==========

class XXModelForm(BootStrapModelForm):
    class Meta:
        model = models.XX
        fields = "__all__"


def tt(request):
    if request.method == "GET":
        form = XXModelForm()
        return render(request, 'tt.html', {"form": form})

    form = XXModelForm(data=request.POST, files=request.FILES)
    if form.is_valid():
        form.save()
    return render(request, 'tt.html', {"form": form})
