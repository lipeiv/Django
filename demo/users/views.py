from django.http import HttpResponse
from django.shortcuts import render
from django.template import loader


def index(request):

    # # 获取模板
    # template = loader.get_template('index.html')
    #
    # # 更改变量字典
    # context = {'city': '北京'}
    #
    # # 渲染模板
    # return HttpResponse(template.render(context))

    context = {'city': '北京',
               'adict': {
                   'name': '西游新记',
                   'author': '吴承恩'
               },
               'alist':[1, 2, 3, 4, 5]
               }

    return render(request, 'index.html', context)
