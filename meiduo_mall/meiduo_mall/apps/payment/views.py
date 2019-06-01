from alipay import AliPay
from django import http
from django.shortcuts import render
from django.conf import settings
# Create your views here.
from django.views import View
import os

from meiduo_mall.utils.response_code import RETCODE
from meiduo_mall.utils.views import LoginRequiredJsonMixin
from orders.models import OrderInfo
from payment.models import Payment


class PaymentStatusView(View):

    def get(self, request):
        '''
        保存支付结果: 订单号+流水号
        :param request:
        :return:
        '''
        # 1. 获取查询字符串字典
        query_dict = request.GET
        data = query_dict.dict()

        # 2. 根据字典获取里面的 sign 的 value值
        signature = data.pop('sign')

        # 3. 创建 工具类(python-alipay-sdk) 的对象
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys/app_private_key.pem"),
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "keys/alipay_public_key.pem"),
            sign_type="RSA2",
            debug=settings.ALIPAY_DEBUG
        )

        # 4. 调用对象的 verify() 进行校验
        success = alipay.verify(data, signature)

        if success:
            # 5. 如果成功: Payment 写入数据(订单号+流水号)
            order_id = data.get('out_trade_no')
            trade_id = data.get('trade_no')
            Payment.objects.create(
                order_id = order_id,
                trade_id = trade_id
            )
            # 6. 订单状态从 未支付 改为 待评价
            OrderInfo.objects.filter(order_id = order_id,
                                     status=OrderInfo.ORDER_STATUS_ENUM['UNPAID']).update(status=OrderInfo.ORDER_STATUS_ENUM['UNCOMMENT'])

            context = {
                'trade_id':trade_id
            }
            # 7. 返回 pay_success.html页面(传入流水号)
            return render(request, 'pay_success.html', context)
        else:
            # 8. 如果未成功: 提示
            return http.HttpResponseForbidden('非法请求')



class PaymentView(LoginRequiredJsonMixin, View):

    def get(self, request, order_id):
        '''
        返回支付宝支付页面的链接
        :param request:
        :param order_id:
        :return:
        '''
        # 1. 校验order_id参数
        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=request.user,
                                          status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'])
        except Exception:
            return http.HttpResponseForbidden('参数出错')

        # 2. 获取 python-alipay-sdk框架的对象
        # 创建支付宝支付对象
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys/app_private_key.pem"),
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "keys/alipay_public_key.pem"),
            sign_type="RSA2",
            debug=settings.ALIPAY_DEBUG
        )

        # 3. 根据对象调用对应的方法, 获取一个字符串(参数)
        # 生成登录支付宝连接
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(order.total_amount),
            subject="美多商城%s" % order_id,
            return_url=settings.ALIPAY_RETURN_URL,
        )

        # 4. 拼接url:  ip + 查询字符串
        alipay_url = settings.ALIPAY_URL + '?' + order_string

        # 5. 返回
        return http.JsonResponse({'code':RETCODE.OK,
                                  'errmsg':'ok',
                                  'alipay_url':alipay_url})
