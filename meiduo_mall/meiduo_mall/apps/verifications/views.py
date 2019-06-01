from django import http
from django.shortcuts import render
from django.views import View
from django_redis import get_redis_connection
# Create your views here.
from meiduo_mall.libs.captcha.captcha import captcha
from meiduo_mall.libs.yuntongxun.ccp_sms import CCP
from meiduo_mall.utils.response_code import RETCODE
from .const import  image_code_expire
from django_redis import get_redis_connection
import logging
logger = logging.getLogger('django')
import random

class SMSCodeView(View):

    def get(self, request, mobile):
        # 获取服务端的图形验证码: redis
        redis_conn = get_redis_connection('verify_code')
        # send_flag = redis_conn.get('send_flag_%s' % mobile)
        # if send_flag:
        #     return http.JsonResponse({'code':RETCODE.THROTTLINGERR, 'errmsg':'发送短信过于频繁'})

        # 1. 接收参数 : 查询字符串: request.GET  表单: request.POST

        # 客户端来的图形验证码:
        image_code_client = request.GET.get('image_code')
        uuid = request.GET.get('image_code_id')

        # 2. 校验
        if not all([image_code_client, uuid]):
            return http.JsonResponse({'code':RETCODE.NECESSARYPARAMERR, 'errmsg':'缺少对应参数'})



        image_code_server = redis_conn.get('img_code_%s' % uuid)
        # 判断服务端验证码是否过期:
        if image_code_server is None:
            return http.JsonResponse({'code':RETCODE.IMAGECODEERR, 'errmsg':'图形验证码已失效'})

        # 立刻删除:
        try:
            redis_conn.delete('img_code_%s' % uuid)
        except Exception as e:
            logger.error(e)

        if image_code_server.decode().lower() != image_code_client.lower():
            return http.JsonResponse({'code':RETCODE.IMAGECODEERR, 'errmsg':'输入的验证码有误'})

        # 3. 生成短信随机验证码:
        sms_code = '%06d' %  random.randint(0, 999999)
        logger.info(sms_code)

        # 获取redis中的管道对象:
        pl = redis_conn.pipeline()

        # 4. 保存到redis:
        pl.setex('sms_code_%s' % mobile, 300, sms_code)
        pl.setex('send_flag_%s' % mobile, 60, 1)

        # 执行管道:
        pl.execute()

        # 5. 发送短信验证码:
        # CCP().send_template_sms(mobile, [sms_code, 5], 1)


        # from celery_tasks.sms.tasks import send_sms_code
        # send_sms_code.delay(mobile, sms_code)

        # 6. 返回:
        return http.JsonResponse({'code':RETCODE.OK, 'errmsg':'ok'})



class ImageCodeView(View):

    def get(self, request, uuid):
        '''
        图形验证码
        :param request:
        :param uuid:
        :return:
        '''

        # 1. 生成图片
        text, image = captcha.generate_captcha()

        # 2. 服务端保存: redis
        # 2.1 创建连接对象:
        redis_conn = get_redis_connection('verify_code')
        # 2.2 保存信息:
        redis_conn.setex('img_code_%s' % uuid, 300, text)  # expire

        # 3. 返回:图片
        return http.HttpResponse(image, content_type='image/jpg')