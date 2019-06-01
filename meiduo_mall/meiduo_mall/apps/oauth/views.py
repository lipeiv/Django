from QQLoginTool.QQtool import OAuthQQ
from django.conf import settings
from django.contrib.auth import login
from django.db import DatabaseError
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django import http
import logging
import re

from carts.utils import merge_cart_cookie_to_redis
from oauth.models import OAuthQQUser
from oauth.utils import generate_access_token, check_access_token
from django_redis import get_redis_connection

from users.models import User

logger = logging.getLogger('django')

from meiduo_mall.utils.response_code import RETCODE


class QQUserView(View):
    def get(self, request):
        '''
        接收code值, 去qq服务器验证, 去数据库中验证是否有该用户
        直接让他登录.
        如果用户不存在,则把openid加密生成token, 返回
        :param request:
        :return:
        '''
        # 1. code的接收
        code = request.GET.get('code')

        # 2. 判断是否存在code
        if not code:
            return http.HttpResponseForbidden('缺少code参数')

        # 3. 获取工具类对象
        # 创建对象
        # 创建对象的时候, 需要传递四个参数:
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                        client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URI)


        try:
            # 4. 调用对象函数, 获取access_token
            access_token = oauth.get_access_token(code)

            # 5. 调用access_token获取openid
            openid = oauth.get_open_id(access_token)
        except Exception as e:
            logger.error(e)

            return http.HttpResponseServerError('oauth2.0认证失败')



        # 6. 判断openid是否在DB中
        try:
            oauth_user = OAuthQQUser.objects.get(openid=openid)
        except OAuthQQUser.DoesNotExist:
            # 8. 如果不存在:
            #    把openid 加密成access_token
            access_token = generate_access_token(openid)

            #    让他重新跳转到下一个绑定页面
            context = {
                'access_token':access_token
            }

            return render(request, 'oauth_callback.html', context=context)

        else:
            # 7. 如果存在:
            qq_user = oauth_user.user
            #    状态保持
            login(request, qq_user)

            #    设置cookie
            response = redirect(reverse('contents:index'))

            response.set_cookie('username', qq_user.username, max_age=3600 * 24 * 14)

            #    重定向到首页
            return response

    def post(self, request):
        '''
        注册用户数据
        :param request:
        :return:
        '''
        # 1. 接收参数
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        sms_code_client = request.POST.get('sms_code')
        access_token = request.POST.get('access_token')

        # 2. 校验参数( mobile, password, sms_code:redis中取,对比,  access_token)
        if not all([mobile, password, sms_code_client]):
            return http.HttpResponseForbidden('缺少必传参数')

        # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('请输入正确的手机号码')

        # 判断密码是否合格
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20位的密码')

        # 创建链接对象
        redis_conn = get_redis_connection('verify_code')

        sms_code_server = redis_conn.get('sms_code_%s' % mobile)
        if sms_code_server is None:
            return render(request, 'oauth_callback.html', {'sms_code_errmsg':'无效的验证码'})

        if sms_code_server.decode() != sms_code_client:
            return render(request, 'oauth_callback.html', {'sms_code_errmsg': '输入的验证码错误'})

        openid = check_access_token(access_token)

        if openid is None:
            return render(request, 'oauth_callback.html', {'openid_errmsg': '过期的access_token'})

        # 3. 查看mobile有没有与之关联的账户
        try:
            user = User.objects.get(mobile=mobile)
        except Exception as e:
            # 4. 如果没有: 新建一个User
            user = User.objects.create_user(username=mobile, password=password, mobile=mobile)
        else:
            if not user.check_password(password):
                return render(request, 'oauth_callback.html', {'account_errmsg': '用户名或者密码错误'})


        # 5. 如果有: 绑定:  创建一个OAuthQQUser 与之绑定
        try:
            OAuthQQUser.objects.create(openid=openid, user=user)
        except DatabaseError:
            return render(request, 'oauth_callback.html', {'qq_login_errmsg': '账户添加失败'})

        login(request, user)

        next = request.GET.get('state')

        if next:
            response = redirect(next)
        else:
            response = redirect(reverse('contents:index'))

        response.set_cookie('username', user.username, max_age=3600 * 24 *14)

        response = merge_cart_cookie_to_redis(request, response)

        return response




class QQURLView(View):

    def get(self, request):
        '''
        返回qq登陆的地址, 方便用户访问qq
        :param request:
        :return:
        '''
        # 1. 接收参数(该参数不是必传)
        next = request.GET.get('next')

        # 2. 生成工具类(QQLoginTool)的对象
        # 创建对象
        # 创建对象的时候, 需要传递四个参数:
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                        client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URI,
                        state=next)

        # 3. 调用函数,生成url
        login_url = oauth.get_qq_url()

        # 4. 返回
        return http.JsonResponse({'code':RETCODE.OK, 'errmsg':'ok', 'login_url':login_url})
