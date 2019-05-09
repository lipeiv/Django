import json

from django.contrib.auth import login, authenticate, logout
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django import http
import re

from goods.models import SKU
from meiduo_mall.utils.response_code import RETCODE

#  此处路径容易错
from meiduo_mall.utils.views import LoginRequiredMixin
from oauth.views import logger
from .models import User

from django.db import DatabaseError
from django_redis import get_redis_connection


class EmailView(View):

    def put(self, request):
        # 1.接收参数
        json_str = request.body.decode()
        json_dict = json.loads(json_str)
        email = json_dict.get('email')

        # 2.校验参数
        if not email:
            return http.HttpResponseForbidden('缺少email参数')

        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return http.HttpResponseForbidden('参数email有误')

        # 3.更改数据库
        try:
            request.user.email = email
            request.user.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '添加邮箱失败'})
        # 4.返回
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '添加邮箱成功'})


class UserInfoView(LoginRequiredMixin, View):

    def get(self, request):
        '''
        提供用户中心页面:
        :param request:
        :return:
        '''
        context = {
            'username': request.user.username,
            'mobile': request.user.mobile,
            'email': request.user.email,
            'email_active': request.user.emai_active,

        }
        return render(request, 'user_center_info.html', context=context)


class LoginView(View):

    def get(self, request):
        return render(request, 'login.html')

    # 1.接收参数
    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        remembered = request.POST.get('remembered')
    # 2.校验
        if not all([username, password]):
            return http.HttpResponseForbidden('缺少参数')

        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('请输入5-20位的用户名')

        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20位的密码')

    # 3.查看账户状态

        user = authenticate(username=username, password=password)
        if user is None:
            return render(request, 'login.html', {'account_errmsg': '用户名或者密码错误'})

    # 4.状态保持
        login(request, user)
        if remembered != 'on':
            request.session.set_expiry(0)
        else:
            request.session.set_expiry(None)

    # 5.返回
        # 响应登录结果
        next = request.GET.get('next')
        if next:
            response = redirect(next)
        else:
            url = reverse('contents:index')
            print(url)
            response = redirect(url)

        # response = redirect(reverse('contents:index'))

        # 登录时用户名写入到cookie，有效期15天
        response.set_cookie('username', user.username, max_age=3600 * 24 * 15)

        return response


class LogoutView(View):
    def get(self, request):
        '''
        退出登录的函数:
        :param request:
        :return:
        '''
        # 1. 退出登录
        logout(request)

        # 2. 清除cookie
        response = redirect(reverse('contents:index'))

        response.delete_cookie('username')

        # 3. 返回
        return response


class MobileCountView(View):

    def get(self, request, mobile):

        # 去数据库中查询该手机号的个数
        count = User.objects.filter(mobile=mobile).count()

        # 返回个数
        return http.JsonResponse({'code': RETCODE.OK,
                                  'errmsg': 'OK',
                                 'count': count})


class UsernameCountView(View):
    # /usernames/(?P<username>[a-zA-Z0-9_-]{5,20})/count/
    def get(self, request, username):

        # 去数据库中查询该用户名的个数
        count = User.objects.filter(username=username).count()

        # 返回个数
        return http.JsonResponse({'code': RETCODE.OK,
                                  'errmsg': 'OK',
                                  'count': count})

class RegisterView(View):

    def get(self, request):

        return render(request, 'register.html')

    def post(self, request):

        # 1. 接收参数
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        mobile = request.POST.get('mobile')
        # TODO sms_code没有接收处理
        sms_code_client = request.POST.get('sms_code')
        allow = request.POST.get('allow')

        # 2. 校验参数
        if not all([username, password, password2, mobile, allow]):
            return http.HttpResponseForbidden('缺少必传参数')

        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('请输入5-20位的用户名')

        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20位的密码')

        # 判断两次密码是否一致:
        if password != password2:
            return http.HttpResponseForbidden('两次输入密码不一致')

        if not re.match(r'^1[345789]\d{9}$', mobile):
            return http.HttpResponseForbidden('请输入正确的手机号')

        # 协议:
        if allow != 'on':
            return http.HttpResponseForbidden('请同意用户协议')

        # 增加的部分: 校验sms_code:
        redis_conn = get_redis_connection('verify_code')
        sms_code_server = redis_conn.get('sms_code_%s' % mobile)
        if sms_code_server is None:
            return render(request, 'register.html', {'sms_code_errmsg':'验证码失效'})

        if sms_code_server.decode() != sms_code_client:
            return render(request, 'register.html', {'sms_code_errmsg': '输入的验证码错误'})

        # 3. 保存
        try:
            user = User.objects.create_user(username=username, password=password, mobile=mobile)
        except  DatabaseError:
            return render(request, 'register.html', {'reigster_errmsg': '保存用户名失败'})

        # 状态保存
        # request.session[] = 'value'
        login(request, user)

        # 4. 返回
        # return http.HttpResponse('注册成功, 应该跳转到首页')
        # return redirect(reverse('contents:index'))
        # 响应登录结果
        response = redirect(reverse('contents:index'))

        # 登录时用户名写入到cookie，有效期15天
        response.set_cookie('username', user.username, max_age=3600 * 24 * 15)

        return response