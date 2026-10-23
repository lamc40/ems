# 联通用户管理系统（EMS）

基于 **Django 4.2 + MySQL + Bootstrap 3** 开发的员工管理系统学习项目，包含部门管理、用户管理、靓号管理三大模块，覆盖 Django Web 开发的核心知识点：ORM 模型设计、ModelForm 表单校验、模板继承、模糊搜索与通用分页组件等。

## 技术栈

| 类别 | 技术 |
|------|------|
| 后端框架 | Django 4.2 |
| 数据库 | MySQL（驱动 mysqlclient 2.3.0） |
| 前端 | Bootstrap 3.4.1 + jQuery 3.6.0（本地静态文件 / CDN） |
| Python | 3.10 / 3.12 |

## 功能模块

### 1. 部门管理
- 部门列表（分页展示）
- 新增部门（两种写法：普通表单 POST / 模板差异版本）
- 编辑部门（URL 传 ID，回显数据）
- 删除部门（删除后**重排剩余部门 ID 并同步更新员工表外键引用**，保持 ID 连续）

### 2. 用户管理
- 用户列表（分页展示，显示部门名称、性别中文等关联/choices 字段）
- 新建用户（手动表单写法）+ 新建用户（ModelForm 写法，字段校验如用户名至少 3 个字符）

### 3. 靓号管理
- 靓号列表（**号码模糊搜索** + 分页展示）
- 新建靓号（ModelForm：手机号正则校验 `^1\d{10}$` + 全表唯一性校验）
- 编辑靓号（唯一性校验排除自身）
- 删除靓号（删除后重排 ID，保持连续）

### 4. 通用分页组件
自研公共组件 `app01/utils/pagination.py`，三个列表页统一复用：

- 基于 queryset 切片分页：第1页 `[0:10]`、第2页 `[10:20]`...，`count()` 计算总页数
- Bootstrap 分页条样式：首页 / 上一页 / 数字页码（当前页蓝色高亮，默认显示当前页 ±5 页）/ 下一页 / 尾页 / 页码输入框 + 跳转按钮
- **搜索 + 分页条件保留**：自动继承 URL 中的全部 GET 参数，翻页链接形如 `?search=156&page=2`，跳转表单通过隐藏域携带搜索条件
- 页码越界保护：非数字页码、超出范围的页码自动修正

视图中使用方式：

```python
from app01.utils.pagination import Pagination

def xxx_list(request):
    queryset = Xxx.objects.all().order_by('id')
    page_object = Pagination(request, queryset)      # 默认每页10条
    return render(request, 'xxx_list.html', {
        'queryset': page_object.page_queryset,       # 当前页数据
        'page_str': page_object.html(),              # 分页条HTML（mark_safe）
    })
```

## 项目结构

```
ems/
├── manage.py                     # Django 管理入口
├── ems/                          # 项目配置目录
│   ├── settings.py               # 配置（含 MySQL 连接信息）
│   ├── urls.py                   # 总路由
│   ├── wsgi.py / asgi.py
└── app01/                        # 业务应用
    ├── models.py                 # 模型：Department / UserInfo / PrettyNum
    ├── admin.py
    ├── apps.py
    ├── migrations/               # 数据库迁移文件
    ├── static/                   # 本地静态资源（bootstrap、jquery）
    ├── templates/                # 模板
    │   ├── layout.html           # 父模板（导航栏 + 页面骨架）
    │   ├── depart_list.html      # 部门列表（分页）
    │   ├── depart_add.html / depart_add2.html / depart_edit.html
    │   ├── user_list.html        # 用户列表（分页）
    │   ├── user_add.html / user_model_form_add.html
    │   ├── pretty_list.html      # 靓号列表（搜索 + 分页）
    │   ├── pretty_add.html / pretty_edit.html
    ├── utils/                    # 公共组件
    │   ├── bootstrap.py          # BootStrapModelForm 基类（统一表单样式）
    │   ├── form.py               # ModelForm 定义（校验规则）
    │   └── pagination.py         # 通用分页组件
    └── views/                    # 视图（按业务模块拆分）
        ├── depart.py             # 部门管理：增删改查
        ├── user.py               # 用户管理：列表、新建
        └── pretty.py             # 靓号管理：增删改查、搜索
```

## 数据模型

| 模型 | 表名 | 主要字段 |
|------|------|----------|
| Department | app01_department | title 部门名称 |
| UserInfo | app01_userinfo | name、password、age、account、create_time、gender（choices 1男/2女）、depart（外键→Department，级联删除） |
| PrettyNum | app01_prettynum | mobile 手机号、price 价格、level（1~4级 choices）、status（已占用/未使用 choices） |
| Admin | app01_admin | username 用户名、password 密码 |

> choices 字段在模板中通过 `get_xxx_display` 显示中文；手机号用字符串存储（避免整型首位 0 丢失/溢出）。

## 路由一览

| URL | 说明 |
|-----|------|
| `/admin/` | Django 自带后台 |
| `/depart/list/` | 部门列表 |
| `/depart/add/`、`/depart/add2/` | 新增部门（两种写法） |
| `/depart/edit/<nid>/` | 编辑部门 |
| `/depart/delete/<nid>/` | 删除部门（重排 ID） |
| `/user/list/` | 用户列表 |
| `/user/add/` | 新建用户（手动表单） |
| `/user/model/form/add/` | 新建用户（ModelForm） |
| `/pretty/list/` | 靓号列表（支持 `?search=` 模糊搜索 + `?page=` 分页） |
| `/pretty/add/` | 新建靓号 |
| `/pretty/edit/<nid>/` | 编辑靓号 |
| `/pretty/delete/<nid>/` | 删除靓号（重排 ID） |

## 快速开始

### 1. 环境准备

```bash
pip install django==4.2 mysqlclient
```

### 2. 创建数据库

在 MySQL 中执行：

```sql
CREATE DATABASE ems DEFAULT CHARSET utf8mb4;
```

### 3. 修改数据库配置

按需修改 `ems/settings.py` 中的数据库连接信息：

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'ems',
        'USER': 'root',
        'PASSWORD': '123456',
        'HOST': '127.0.0.1',
        'PORT': 3306,
    }
}
```

### 4. 执行数据库迁移

```bash
python manage.py migrate
```

### 5. 启动服务

```bash
python manage.py runserver 8000
```

浏览器访问 <http://127.0.0.1:8000/depart/list/> 即可进入系统。

## 学习要点索引

- **ModelForm 统一样式**：`utils/bootstrap.py` 定义 `BootStrapModelForm` 基类，重写 `__init__` 循环给所有字段添加 `form-control` 类和 placeholder，各表单继承即可
- **字段级校验钩子**：`utils/form.py` 中 `clean_mobile` 实现手机号唯一性校验（编辑时用 `exclude(id=self.instance.pk)` 排除自身）
- **choices 字段**：模型定义选项元组，模板用 `get_xxx_display` 渲染中文
- **模板继承**：所有页面继承 `layout.html`，通过 `{% block %}` 扩展标题/内容/CSS/JS
- **删除后重排 ID**：原生 SQL + 临时关闭外键检查（`SET FOREIGN_KEY_CHECKS=0`），更新主键及外键引用后重置自增计数器
- **通用分页组件**：`app01/utils/pagination.py`，queryset 切片 + URL 参数继承（搜索条件不丢失）
