import json
from decimal import Decimal

from django import http
from django.core.paginator import Paginator, EmptyPage
from django.db import transaction
from django.shortcuts import render

# Create your views here.
from django.utils import timezone
from django.views import View
from django_redis import get_redis_connection

from goods.models import SKU
from meiduo_mall.utils.response_code import RETCODE
from meiduo_mall.utils.views import LoginRequiredMixin, LoginRequiredJsonMixin
from orders.models import OrderInfo, OrderGoods
from users.models import Address
import logging
logger = logging.getLogger('django')


class UserOrderInfoView(LoginRequiredMixin, View):

    def get(self, request, page_num):
        # 1. 获取用户
        user = request.user

        # 2. 根据用户,获取他的所有订单
        orders = user.orderinfo_set.all().order_by('-create_time')

        # 3. 遍历订单, 拿到每一个
        for order in orders:
            # 4. 订单状态名称
            order.status_name = OrderInfo.ORDER_STATUS_CHOICES[order.status-1][1]
            # 5. 订单支付名称
            order.pay_method_name = OrderInfo.PAY_METHOD_CHOICES[order.pay_method - 1][1]
            # 6. 获取所有商品
            order_goods = order.skus.all()

            order.sku_list = []
            # 7. 遍历所有商品, 获取每一行
            for order_good in order_goods:
                # 8. 更新数据:  sku  count amount
                sku = order_good.sku
                sku.count = order_good.count
                sku.amount = sku.price * sku.count
                order.sku_list.append(sku)

        # 9. 获取page_num
        page_num = int(page_num)

        # 10. 创建分页对象
        try:
            paginator = Paginator(orders, 1)
            # 11. 获取当前页的数据
            # 12 获取总页吗
            page_orders = paginator.page(page_num)
            total_page = paginator.num_pages
        except EmptyPage:
            return http.HttpResponseNotFound('当前页找不到')

        # 13 组织数据
        context = {
            "page_orders": page_orders,
            'total_page': total_page,
            'page_num': page_num,
        }
        # 14 返回
        return render(request, 'user_center_order.html', context)







class OrderSuccessView(LoginRequiredMixin, View):

    def get(self, reqeust):
        order_id = reqeust.GET.get('order_id')
        payment_amount = reqeust.GET.get('payment_amount')
        pay_method = reqeust.GET.get('pay_method')

        context = {
            'order_id':order_id,
            'payment_amount':payment_amount,
            'pay_method':pay_method
        }

        return render(reqeust, 'order_success.html', context)





class OrderCommitView(LoginRequiredJsonMixin, View):

    def post(self, request):
        '''
        保存订单信息
        :param request:
        :return:
        '''

        # 1.获取参数: address_id  pay_method
        json_dict = json.loads(request.body.decode())
        address_id = json_dict.get('address_id')
        pay_method = json_dict.get("pay_method")

        # 2.校验参数
        if not all([address_id, pay_method]):
            return http.HttpResponseForbidden('缺少必传参数')

        try:
            address = Address.objects.get(id=address_id)
        except Exception:
            return http.HttpResponseForbidden('参数address_id有误')

        if pay_method not in [OrderInfo.PAY_METHODS_ENUM['CASH'],
                              OrderInfo.PAY_METHODS_ENUM['ALIPAY']]:
            return http.HttpResponseForbidden('参数pay_method有误')

        user = request.user
        # 创建一个订单编号
        order_id = timezone.localtime().strftime('%Y%m%d%H%M%S') + ('%09d' % user.id)

        with transaction.atomic():
            save_id = transaction.savepoint()
            try:
                # 3.订单保存
                order = OrderInfo.objects.create(
                    order_id = order_id,
                    user = user,
                    address = address,
                    total_count=0,
                    total_amount=Decimal('0.00'),
                    freight=Decimal('10.00'),
                    pay_method=pay_method,
                    status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'] if pay_method == OrderInfo.PAY_METHODS_ENUM['ALIPAY'] else OrderInfo.ORDER_STATUS_ENUM['UNSEND']
                )

                # 4. 链接redis
                redis_conn = get_redis_connection('carts')
                # 5. 获取 hash set 的数据
                #    hash:  count(销售)  set:sku_ids
                item_dict = redis_conn.hgetall('carts_%s' % user.id)
                cart_selected = redis_conn.smembers('selected_%s' % user.id)

                cart = {}
                # 6.  整理格式
                for sku_id in cart_selected:
                    cart[int(sku_id)] = int(item_dict[sku_id])

                # 7. 遍历: 每一个商品id, 根据商品id 获取 sku(商品)
                for sku_id in cart.keys():
                    while True:
                        # 商品:
                        sku = SKU.objects.get(id=sku_id)
                        # 销量:
                        sku_count = cart[sku.id]

                        origin_stock = sku.stock
                        origin_sales = sku.sales

                        # 8. 比较 库存和销量的关系
                        if sku_count > sku.stock:
                            transaction.savepoint_rollback(save_id)
                            return http.JsonResponse({'code':RETCODE.STOCKERR,
                                                      'errmsg':'库存不足'})


                        # 9. 减少库存 增加销量
                        # sku.stock -= sku_count
                        # sku.sales += sku_count
                        # sku.save()

                        new_stock = origin_stock - sku_count
                        new_sales = origin_sales + sku_count

                        result = SKU.objects.filter(id=sku_id, stock=origin_stock).update(stock=new_stock, sales=new_sales)
                        if result == 0:
                            continue

                        # 10. spu更新id
                        sku.goods.sales += sku_count
                        sku.goods.save()

                        # 11. 存入 OrderGoods
                        OrderGoods.objects.create(
                            order = order,
                            sku = sku,
                            count=sku_count,
                            price=sku.price
                        )

                        # 12. 更新订单表中的初始化字段 total_count total_amount
                        order.total_count += sku_count
                        order.total_amount += (sku.price * sku_count)
                        break

                 # 13. total_amount + 运费, 保存
                order.total_amount += order.freight
                order.save()
            except Exception as e:
                logger.error(e)
                transaction.savepoint_rollback(save_id)
                return http.JsonResponse({'code':RETCODE.DBERR,
                                  'errmsg':'存储失败'})
            transaction.savepoint_commit(save_id)

         # 14. 把redis中关于当前订单的删除
        redis_conn.hdel('carts_%s' % user.id, *cart_selected)
        redis_conn.srem('selected_%s' % user.id, *cart_selected)

         # 15. 返回
        return http.JsonResponse({'code':RETCODE.OK,
                                  'errmsg':'ok',
                                  'order_id':order.order_id})








class OrderSettlementView(LoginRequiredMixin, View):

    def get(self, request):
        '''
        返回订单页面(place_order.html)
        :param request:
        :return:
        '''
        # 1.获取登录用户
        user = request.user

        # 2.获取地址(当前用户的所有地址)
        try:
            addresses = Address.objects.filter(user=user,
                                               is_deleted=False)
        except Address.DoesNotExist:
            addresses = None

        # 3.链接redis, 获取 hash 和 set中的东西
        redis_conn = get_redis_connection('carts')
        item_dict = redis_conn.hgetall('carts_%s' % user.id)
        cart_selected = redis_conn.smembers('selected_%s' % user.id)

        cart = {}
        # 4.拼接数据(把 sku_id 和 count 拼接到一起)
        for sku_id in cart_selected:
            cart[int(sku_id)] = int(item_dict.get(sku_id))

        # 5.total_count + total_amount
        total_count = 0
        total_amount = Decimal('0.00')

        # 6.获取商品,整合商品信息
        skus = SKU.objects.filter(id__in=cart.keys())
        for sku in skus:
            sku.count = cart.get(sku.id)
            sku.amount = sku.price * sku.count

            total_count += sku.count
            total_amount += sku.amount

        freight = Decimal('10.00')

        # 7.拼接数据
        context = {
            'addresses':addresses,
            'skus':skus,
            'total_count':total_count,
            'total_amount':total_amount,
            'freight':freight,
            'payment_amount': total_amount + freight
        }

        # 8.返回
        return render(request, 'place_order.html', context)