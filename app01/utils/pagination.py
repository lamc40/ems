""" 分页公共组件：列表页传入 queryset 即可完成分页，并生成 Bootstrap 风格的分页条 """
import copy

from django.utils.html import escape
from django.utils.safestring import mark_safe


class Pagination(object):
    """ 基于 queryset 切片实现的分页类

    用法（视图函数中）：
        page_object = Pagination(request, queryset)        # 默认每页10条
        context = {"queryset": page_object.page_queryset,  # 当前页数据（切片后的queryset）
                   "page_str": page_object.html()}         # 分页条HTML（模板中直接渲染）
    """

    def __init__(self, request, queryset, page_size=10, page_param="page", plus=5):
        # 1. 复制当前URL中的所有GET参数（如搜索关键字），
        #    生成链接/跳转时原样带上，解决"搜索+分页丢失搜索条件"的问题
        query_dict = copy.deepcopy(request.GET)
        query_dict._mutable = True          # QueryDict默认不可修改，复制后放开限制
        self.query_dict = query_dict
        self.page_param = page_param

        # 2. 获取当前页码：URL中无page参数或不是纯数字时，默认第1页
        page = request.GET.get(page_param, "1")
        if page.isdecimal():
            page = int(page)
        else:
            page = 1

        self.page_size = page_size          # 每页显示条数
        self.plus = plus                    # 当前页左右两侧各显示的页码个数

        # 3. 计算总页数：总条数 / 每页条数，除不尽时补1页
        total_count = queryset.count()      # 等价于 models.Xxx.objects.all().count()
        total_page_count, div = divmod(total_count, page_size)
        if div:
            total_page_count += 1
        self.total_page_count = total_page_count

        # 页码越界保护：小于1回到第1页，大于总页数回到最后一页
        if page < 1:
            page = 1
        elif total_page_count > 0 and page > total_page_count:
            page = total_page_count
        self.page = page

        # 4. 计算切片位置：第1页[0:10]、第2页[10:20]、第3页[20:30]...
        self.start = (page - 1) * page_size
        self.end = page * page_size
        # 当前页数据：等价于 queryset[起始位置:结束位置]
        self.page_queryset = queryset[self.start:self.end]

    def html(self):
        """ 生成分页条HTML（图2样式）：首页/上一页/数字页码(当前页高亮)/下一页/尾页/跳转 """
        # 只有1页（或没有数据）时无需显示分页条
        if self.total_page_count <= 1:
            return ""

        # 先把page参数从参数字典中去掉，剩余参数（如搜索条件）做成跳转表单的隐藏域
        self.query_dict.pop(self.page_param, None)
        hidden_inputs = "".join(
            ['<input type="hidden" name="{}" value="{}">'.format(escape(k), escape(v))
             for k, v in self.query_dict.items()]
        )

        def page_url(page_number):
            """ 生成带所有原GET参数的分页链接，仅覆盖page参数 """
            self.query_dict[self.page_param] = page_number
            return "?{}".format(self.query_dict.urlencode())

        page_list = []
        # ---------- 首页 ----------
        page_list.append('<li><a href="{}">首页</a></li>'.format(page_url(1)))
        # ---------- 上一页 ----------
        prev_page = self.page - 1 if self.page > 1 else 1
        page_list.append('<li><a href="{}">上一页</a></li>'.format(page_url(prev_page)))
        # ---------- 数字页码：只显示 [当前页-plus, 当前页+plus] 范围内的页码 ----------
        for i in range(self.page - self.plus, self.page + self.plus + 1):
            if i < 1 or i > self.total_page_count:
                continue
            if i == self.page:
                # 当前页：bootstrap的active样式（蓝色高亮）
                page_list.append('<li class="active"><a href="{}">{}</a></li>'.format(page_url(i), i))
            else:
                page_list.append('<li><a href="{}">{}</a></li>'.format(page_url(i), i))
        # ---------- 下一页 ----------
        next_page = self.page + 1 if self.page < self.total_page_count else self.total_page_count
        page_list.append('<li><a href="{}">下一页</a></li>'.format(page_url(next_page)))
        # ---------- 尾页 ----------
        page_list.append('<li><a href="{}">尾页</a></li>'.format(page_url(self.total_page_count)))

        # ---------- 跳转：页码输入框 + 跳转按钮（GET提交，隐藏域保留搜索条件） ----------
        jump = """<li>
                    <form method="get" action="" style="display: inline; margin-left: -1px;">
                        {hidden}
                        <input type="text" name="{param}" class="form-control" placeholder="页码"
                               style="display: inline-block; width: 80px; border-radius: 0;">
                        <button type="submit" class="btn btn-default" style="border-radius: 0;">跳转</button>
                    </form>
                </li>""".format(hidden=hidden_inputs, param=self.page_param)

        html = '<ul class="pagination" style="margin: 10px 0;">{}{}</ul>'.format(
            "".join(page_list), jump)
        # 标记为安全HTML，模板中 {{ page_str }} 才能直接渲染成标签而不是转义文本
        return mark_safe(html)
