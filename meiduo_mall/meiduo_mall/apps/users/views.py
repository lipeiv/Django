from django.contrib.auth import login, authenticate, logout
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django import http
import re
import json

from carts.utils import merge_cart_cookie_to_redis
from goods.models import SKU
from meiduo_mall.utils.response_code import RETCODE
from meiduo_mall.utils.views import LoginRequiredMixin, LoginRequiredJsonMixin
from .models import User, Address
from django.db import DatabaseError
from django_redis import get_redis_connection
import logging
logger = logging.getLogger('django')


class UserBrowseHistory(LoginRequiredJsonMixin, View):

    def get(self, request):
        '''
        返回用户浏览记录(记录的商品数据)
        :param request:
        :return:
        '''
        # 1. 创建redis链接对象
        redis_conn = get_redis_connection('history')

        # 2. 获取sku_ids(value): lrange(key, 开始位置, 结束为止)
        sku_ids = redis_conn.lrange('history_%s' % request.user.id, 0, -1)

        # 3. 遍历:
        skus = []
        for sku_id in sku_ids:
            # 4. 根据id获取商品信息
            sku = SKU.objects.get(id=sku_id)

            # 5. 拼接商品信息
            skus.append({
                'id':sku.id,
                'name':sku.name,
                'default_image_url':sku.default_image_url,
                'price':sku.price
            })

        # 6. 返回
        return http.JsonResponse({'code':RETCODE.OK,
                                  'errmsg':'ok',
                                  'skus':skus})
    
    def post(self, request):
        '''
        保存用户浏览记录
        :param request: 
        :return: 
        '''
        # 1.接收sku_id参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')

        # 2.校验参数
        try:
            SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('sku_id不正确')

        # 3.链接redis
        redis_conn = get_redis_connection('history')
        pl = redis_conn.pipeline()
        user_id = request.user.id

        # 4.去重
        pl.lrem('history_%s' % user_id, 0, sku_id)

        # 5.存储
        pl.lpush('history_%s' % user_id, sku_id)

        # 6.截取
        pl.ltrim('history_%s' % user_id, 0, 4)

        # 管道执行:
        pl.execute()

        # 7.返回
        return http.JsonResponse({'code': RETCODE.OK,
                                  'errmsg': 'ok'})


class ChangePasswordView(LoginRequiredMixin, View):
    def get(self, request):
        '''
        返回更改密码页面
        :param request:
        :return:
        '''
        return render(request, 'user_center_pass.html')

    def post(self, request):
        '''
        更改密码的接口
        :param request:
        :return:
        '''
        # 1. 接收参数
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        new_password2 = request.POST.get('new_password2')

        # 2. 校验参数 (老密码校验, 新密码加密)
        if not all([old_password, new_password, new_password2]):
            return http.HttpResponseForbidden('缺少必传参数')

        try:
            request.user.check_password(old_password)
        except Exception as  e:
            logger.error(e)
            return render(request, 'user_center_pass.html', {'origin_pwd_errmsg':'原始密码有错'})

        if not re.match(r'^[a-zA-Z0-9]{8,20}$', new_password):
            return http.HttpResponseForbidden('密码需要8到20位')

        if new_password != new_password2:
            return http.HttpResponseForbidden('两次输入的密码不一致')

        # 3. 保存(新密码加密)
        try:
            request.user.set_password(new_password)
            request.user.save()
        except Exception as  e:
            logger.error(e)
            return render(request, 'user_center_pass.html', {'change_pwd_errmsg': '更新密码有误'})

        # 4. 清除状态(session, cookie)
        logout(request)

        response = redirect(reverse('users:login'))

        response.delete_cookie('username')

        # 5. 跳转到登录页面
        return response


class UpdateTitleAddressView(LoginRequiredJsonMixin, View):

    def put(self, request, address_id):

        json_dict = json.loads(request.body.decode())
        title = json_dict.get('title')

        try:
            address = Address.objects.get(id=address_id)

            address.title = title
            address.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code':RETCODE.DBERR, 'errmsg':'修改标题失败'})

        return http.JsonResponse({'code':RETCODE.OK, 'errmsg':'ok'})


class DefaultAddressView(LoginRequiredJsonMixin, View):

    def put(self, request, address_id):
        '''
        设置默认地址
        :param request:
        :param address_id:
        :return:
        '''
        try:
            address = Address.objects.get(id=address_id)

            request.user.default_address = address
            request.user.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code':RETCODE.DBERR, 'errmsg':'设置默认地址失败'})

        return http.JsonResponse({'code':RETCODE.OK, 'errmsg':'ok'})


class UpdateDestroyAddressView(LoginRequiredJsonMixin, View):

    def delete(self, request, address_id):
        try:
            address = Address.objects.get(id=address_id)

            address.is_deleted = True
            address.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code':RETCODE.DBERR,
                                      'errmsg':'删除失败'})

        return http.JsonResponse({'code': RETCODE.OK,
                                  'errmsg': 'ok'})




    def put(self, request, address_id):
        '''
        修改address_id对应的地址
        :param request:
        :param address_id:
        :return:
        '''
        # 1. 获取参数
        json_dict = json.loads(request.body.decode())
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        # 2. 校验参数
        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('参数mobile有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')


        # 3. 修改 如果报错,处理
        try:
            Address.objects.filter(id=address_id).update(
                user=request.user,
                title=receiver,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code':RETCODE.DBERR,
                                      'errmsg': '修改地址失败'})

        address = Address.objects.get(id=address_id)
        # 4. 拼接参数,返回响应
        address_dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "city": address.city.name,
            "district": address.district.name,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email
        }
        return http.JsonResponse({'code': RETCODE.OK,
                                  'errmsg': 'ok',
                                  'address':address_dict})


class CreateAddressView(LoginRequiredJsonMixin, View):

    def post(self, request):

        # 1. 获取数量,判断是否超过20
        count = request.user.addresses.count()

        if count >= 20:
            return http.JsonResponse({'code':RETCODE.THROTTLINGERR,
                                      'errmsg':'超过地址上限'})

        # 2. 接收参数
        json_dict = json.loads(request.body.decode())
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        # 3. 校验
        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('参数mobile有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')

        # 4. 存储
        try:
            address = Address.objects.create(
                user = request.user,
                title = receiver,
                receiver = receiver,
                province_id = province_id,
                city_id = city_id,
                district_id = district_id,
                place = place,
                mobile = mobile,
                tel = tel,
                email = email
            )

            # 4.1 设置默认地址:
            if not request.user.default_address:
                request.user.default_address = address
                request.user.save()

        except Exception as e:
            return http.JsonResponse({'code':RETCODE.DBERR,
                                      'errmsg':'数据库保存失败'})

        # 5. 拼接参数,准备返回
        address_dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "city": address.city.name,
            "district": address.district.name,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email
        }

        # 6. 返回
        return http.JsonResponse({'code':RETCODE.OK,
                                  'errmsg':'ok',
                                  'address':address_dict})


class AddressView(LoginRequiredMixin, View):

    def get(self, request):
        '''
        返回地址页面:user_center_site.html
        :param request:
        :return:
        '''

        # 1. 取出当前用户的所有地址
        addresses = Address.objects.filter(user=request.user, is_deleted=False)

        addres_dict_list = []

        # 2. 遍历拿出每一个地址
        for address in addresses:
            # 3. 整理数据 ---> 保存字典中 ---> 把所有的地址放到一个list中
            address_dict = {
                'id':address.id,
                'title':address.title,
                'receiver':address.receiver,
                'province':address.province.name,
                "city": address.city.name,
                "district": address.district.name,
                "place": address.place,
                "mobile": address.mobile,
                "tel": address.tel,
                "email": address.email
            }

            # 4. 查出默认地址, 把它放到最上边(list)
            if request.user.default_address.id == address.id:
                # 4.1 查出默认地址
                addres_dict_list.insert(0, address_dict)
            else:
                # 普通地址:
                addres_dict_list.append(address_dict)
        # 5. 返回
        context = {
            'default_address_id':request.user.default_address_id,
            'addresses': addres_dict_list
        }

        return render(request, 'user_center_site.html', context=context)


class VerifyEmailView(View):

    def get(self, request):
        token = request.GET.get('token')

        if not token:
            return http.HttpResponseForbidden('缺少token参数')

        user = User.check_verify_email_token(token)
        if user is None:
            return http.HttpResponseForbidden('无效的token')


        try:
            user.email_active = True
            user.save()
        except Exception as e:
            logger.error(e)
            return http.HttpResponseServerError('修改邮箱验证失败')

        return redirect(reverse('users:info'))


class EmailView(LoginRequiredJsonMixin, View):

    def put(self, request):
        '''
        接收邮箱,保存到数据库中
        :param request:
        :return:
        '''
        # 1. 接收参数
        # request.POST
        # request.GET
        # json_str = request.body.decode()
        # json_dict = json.loads(json_str)
        # email = json_dict.get('email')

        json_dict = json.loads(request.body.decode())
        email = json_dict.get('email')


        # 2. 校验参数
        if not email:
            return http.HttpResponseForbidden('缺少email参数')

        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return http.HttpResponseForbidden('email格式不正确')

        # 3. 更改数据库
        # User.objects.update()
        try:
            request.user.email = email
            request.user.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code':RETCODE.DBERR, 'errmsg':'保存邮箱失败'})

        # 发送验证邮件:
        from celery_tasks.email.tasks import send_verify_email
        verify_url = request.user.generate_verify_email_token()
        send_verify_email.delay(email, verify_url)

        # 4. 返回
        return http.JsonResponse({'code':RETCODE.OK, 'errmsg':'邮箱保存成功'})


class UserInfoView(LoginRequiredMixin, View):

    def get(self, request):
        '''
        提供用户中心页面:
        :param request:
        :return:
        '''

        context = {
            'username':request.user.username,
            'mobile':request.user.mobile,
            'email':request.user.email,
            'email_active':request.user.email_active
        }

        return render(request, 'user_center_info.html', context=context)


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


class LoginView(View):

    def get(self, request):
        '''
        返回前端需要的登录页面
        :param request:
        :return: 登录页面
        '''
        return render(request, 'login.html')

    def post(self, request):
        '''
        接收登录请求, 进行验证,查看是否能够登录
        :param request:
        :return: 返回首页
        '''
        # 1. 接收参数
        username = request.POST.get('username')
        password = request.POST.get('password')
        remembered = request.POST.get('remembered')

        # 2. 校验
        if not all([username, password]):
            return http.HttpResponseForbidden('缺少参数')

        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('请输入5-20位的用户名')

        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20位的密码')

        # 3. 查看是否存在该账户
        user = authenticate(username=username, password=password)

        if user is None:
            return render(request, 'login.html', {'account_errmsg':'用户名或密码错误'})

        # 4. 状态保持
        login(request, user)

        if remembered != 'on':
            # 用户没有勾选记住登录:
            request.session.set_expiry(0)
        else:
            # 用户勾选记住登录: 默认有效期: 两周
            request.session.set_expiry(None)

        # 5. 返回
        # return redirect(reverse('contents:index'))

        # 获取查询字符串:
        next = request.GET.get('next') # /info/

        if next:

            response = redirect(next)

        else:
            url = reverse('contents:index')
            # print(url)

            response = redirect(url)

        # 设置cookie: 有效期为15天
        response.set_cookie('username', user.username, max_age=3600 * 24 * 15)

        response = merge_cart_cookie_to_redis(request, response)

        return response


class MobileCountView(View):

    def get(self, request, mobile):
        '''
        获取手机号,查询手机号数量,并返回
        :param request:
        :param username:
        :return:
        '''
        # 去数据库中查询该手机号的个数
        count = User.objects.filter(mobile=mobile).count()

        # 返回个数
        return http.JsonResponse({'code':RETCODE.OK,
                                  'errmsg':'OK',
                                  'count': count})


class UsernameCountView(View):
    # /usernames/(?P<username>[a-zA-Z0-9_-]{5,20})/count/
    def get(self, request, username):
        '''
        获取用户名,查询用户名数量,并返回
        :param request:
        :param username:
        :return:
        '''

        # 去数据库中查询该用户名的个数
        count = User.objects.filter(username=username).count()

        # 返回个数
        return http.JsonResponse({'code':RETCODE.OK,
                                  'errmsg':'OK',
                                  'count': count})


class RegisterView(View):

    def get(self, request):
        '''
        返回给前端 注册页面
        :param request: 请求对象
        :return: 注册页面的地址
        '''
        return render(request, 'register.html')

    def post(self, request):
        '''
        接收前端传入的表单信息, 进行用户的增加
        :param request:
        :return:
        '''
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
            return render(request, 'reigster.html', {'sms_code_errmsg':'验证码失效'})

        if sms_code_server.decode() != sms_code_client:
            return render(request, 'reigster.html', {'sms_code_errmsg': '输入的验证码错误'})



        # 3. 保存
        try:
            user = User.objects.create_user(username=username, password=password, mobile=mobile)
        except  DatabaseError:
            return render(request, 'register.html', {'reigster_errmsg':'保存用户名失败'})


        # 状态保存
        # request.session[] = 'value'
        login(request, user)


        # 4. 返回
        # return http.HttpResponse('注册成功, 应该跳转到首页')
        # return redirect(reverse('contents:index'))

        response = redirect(reverse('contents:index'))

        # 设置cookie: 有效期为15天
        response.set_cookie('username', user.username, max_age=3600 * 24 * 15)

        return response