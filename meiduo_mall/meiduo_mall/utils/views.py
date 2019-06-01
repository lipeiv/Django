from django import http
from django.contrib.auth.decorators import login_required
from django.utils.decorators import wraps

from meiduo_mall.utils.response_code import RETCODE


class LoginRequiredMixin(object):
    '''
       作用: 检验用户是否登录, 如果没有登录, 跳转到login页面
    '''

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view()
        return login_required(view)


def login_required_json(view_func):

    # @wraps: 返回view_func的函数名和文档
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated():
            # 没有登录:
            return http.JsonResponse({'code':RETCODE.SESSIONERR, 'errmsg':'用户未登录'})
        else:
            # 登陆过:
            return view_func(request, *args, **kwargs)

    return wrapper



class LoginRequiredJsonMixin(object):
    '''
    作用: 检验用户是否登录, 如果没有登录,返回json格式的结果
    '''
    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view()
        return login_required_json(view)






    # def view(self):
    #     '''
    #     111
    #     :return:
    #     '''
    #     pass
    #
    # help(view)  # 111
    # view ----> view()
    #
    #
    #
    #
    #
    #
    # @viewfunc(view)    #  == = > view = viewfunc(view)
    # def view(self):
    #     '''
    #     1111
    #     :return:
    #     '''
    #     pass
    #
    # help(view)  # 222
    # view ----> wrapper
    #
    #
    #
    # @viewfunc(view)    #  == = > view = viewfunc(view)
    # def func(self):
    #     '''
    #     1111
    #     :return:
    #     '''
    #     pass
    #
    # help(view)  # 222