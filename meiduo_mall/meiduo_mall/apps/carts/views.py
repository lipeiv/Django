import base64
import pickle

from django import http
from django.shortcuts import render

# Create your views here.
from django.views import View
import json
from django_redis import get_redis_connection
from goods.models import SKU
from meiduo_mall.utils.response_code import RETCODE

class CartsSimpleView(View):
    def get(self, request):
        # 1. 判断是否登录
        user = request.user
        if user.is_authenticated:

            # 2. 如果登录: 链接redis
            redis_conn = get_redis_connection('carts')

            # 3. 从hash中取值, 从set取值
            item_dict = redis_conn.hgetall('carts_%s' % user.id)
            cart_selected = redis_conn.smembers('selected_%s' % user.id)

            # 4. 拼接成 cookie的格式
            cart_dict = {}
            for sku_id, count in item_dict.items():
                cart_dict[int(sku_id)] = {
                    'count':int(count),
                    'selected': sku_id in cart_selected
                }

        else:
            # 5. 未登录:
            # 6. 获取cookie: 判断+解密
            cookie_cart = request.COOKIES.get('carts')
            if cookie_cart:
                cart_dict = pickle.loads(base64.b64decode(cookie_cart))
            else:
                cart_dict = {}

        # 7.统一处理:
        # 8.获取sku_ids
        sku_ids = cart_dict.keys()

        # 9. 根据id 获取 skus
        skus = SKU.objects.filter(id__in=sku_ids)

        cart_skus = []
        # 10 遍历, 拿到单个商品, 拼接参数
        for sku in skus:
            cart_skus.append({
                'id':sku.id,
                'name':sku.name,
                'count':str(cart_dict.get(sku.id).get('count')),
                'default_image_url':sku.default_image_url
            })

        # 11. 返回
        return http.JsonResponse({'code':RETCODE.OK,
                                  'errmsg':'ok',
                                  'cart_skus':cart_skus})




class CartSelectAllView(View):

    def put(self, request):
        '''
        修改是否全选的接口
        :param request:
        :return:
        '''
        # 1. 接受参数selected
        json_dict = json.loads(request.body.decode())
        selected = json_dict.get('selected', True)

        # 2. 校验
        if selected:
            if not isinstance(selected, bool):
                return http.HttpResponseForbidden('参数selected有误')

        # 3. 判断是否登录
        user = request.user
        if user.is_authenticated:
            # 4. 登陆了, 链接redis
            redis_conn = get_redis_connection('carts')

            # 5. 获取 hash 标的所有的 键
            item_dict = redis_conn.hgetall('carts_%s' % user.id)
            sku_ids = item_dict.keys()

            # 6. 判断参数selected 是否为真:  把所有的键保存进去
            if selected:
                redis_conn.sadd('selected_%s' % user.id, *sku_ids)
            else:
            # 7. 如果为假: 删除所有的 set表
                redis_conn.srem('selected_%s' % user.id, *sku_ids)

            # 8. 返回
            return http.JsonResponse({'code':RETCODE.OK,
                                      'errmsg':'全选成功'})

        else:
            # 未登录:
            # 1. 获取cookie
            cookie_cart = request.COOKIES.get('carts')

            response = http.JsonResponse({'code':RETCODE.OK,
                                          'errmsg':'全选成功'})

            # 2. 判断cookie  解密 dict
            if cookie_cart:
                # cart_dict = {
                #     'sku_id':{
                #         'count':2,
                #         'selected':True
                #     }
                # }


                cart_dict = pickle.loads(base64.b64decode(cookie_cart))

                # 3. 根据selectd 为真:  更新 dict中的seleted为true
                #  为假: 更新 dict中的seleted为false
                for sku_id in cart_dict.keys():
                    cart_dict[sku_id]['selected'] = selected

                # 4.返回
                cart_data = base64.b64encode(pickle.dumps(cart_dict)).decode()

                response.set_cookie('carts', cart_data)

            return response

class CartsView(View):

    def delete(self, request):
        '''
        删除某一个商品
        :param request:
        :return:
        '''
        # 1.获取用户传入的参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')

        # 2.校验
        try:
            SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('参数sku_id有误')

        # 3.判断是否登录
        if request.user.is_authenticated:
            # 4.如果登录:  链接redis
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()

            # 5.删除:  hash + set
            pl.hdel('carts_%s' % request.user.id, sku_id)
            pl.srem('selected_%s' % request.user.id, sku_id)

            pl.execute()
            # 6.返回
            return http.JsonResponse({'code':RETCODE.OK,
                                      'errmsg':'删除成功'})
        else:
            # 7.如果未登录:
            # 8. 获取cookie
            cookie_cart = request.COOKIES.get('carts')

            # 9. 判断cookie是否存在
            if cookie_cart:
                # 10. 如果存在, 解密,
                cart_dict = pickle.loads(base64.b64decode(cookie_cart))
            else:
                # 如果不存在, 创建
                cart_dict = {}

            response = http.JsonResponse({'code': RETCODE.OK,
                                          'errmsg': 'ok'})

            # 11. 根据sku_id删除 对应的商品
            if sku_id in cart_dict:
                del cart_dict[sku_id]
                # 12. 加密
                cart_data = base64.b64encode(pickle.dumps(cart_dict)).decode()

                # 13. 返回
                response.set_cookie('carts', cart_data)

            return response


    def put(self, request):
        '''
        修改购物车数据
        :param request:
        :return:
        '''
        # 1.获取参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected', True)

        # 2.校验参数
        if not all([sku_id, count]):
            return http.HttpResponseForbidden('缺少必传参数')

        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('参数sku_id有误')

        try:
            count = int(count)
        except Exception:
            return http.HttpResponseForbidden('参数count有误')

        if selected:
            if not isinstance(selected, bool):
                return http.HttpResponseForbidden('参数selected有误')

        # 3.获取用户, 判断是否登录
        user = request.user
        if user.is_authenticated:
            # 1.链接redis
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()

            # 2.修改hash的值
            pl.hset('carts_%s' % user.id, sku_id, count)

            # 3.修改set表的值
            if selected:
                pl.sadd('selected_%s' % user.id, sku_id)
            else:
                pl.srem('selected_%s' % user.id, sku_id)

            pl.execute()

            # 4.组织数据
            cart_sku = {
                'id':sku.id,
                'name':sku.name,
                'count':count,
                'price':sku.price,
                'amount':sku.price * count,
                'default_image_url':sku.default_image_url,
                'selected':selected
            }

            # 5.返回
            return http.JsonResponse({'code':RETCODE.OK,
                                      'errmsg':'修改成功',
                                      'cart_sku':cart_sku})

        else:
            # 1. 获取cookie
            cookie_cart = request.COOKIES.get('carts')
            if cookie_cart:
                # 2. 解码
                cart_dict = pickle.loads(base64.b64decode(cookie_cart))
            else:
                cart_dict = {}

            # 3. 修改数据
            cart_dict[sku_id] = {
                'count':count,
                'selected':selected
            }

            cart_data = base64.b64encode(pickle.dumps(cart_dict)).decode()

            # 4. 构造数据
            cart_sku = {
                'id': sku.id,
                'name': sku.name,
                'count': count,
                'price': sku.price,
                'amount': sku.price * count,
                'default_image_url': sku.default_image_url,
                'selected': selected
            }

            response = http.JsonResponse({'code': RETCODE.OK,
                                      'errmsg': '修改成功',
                                      'cart_sku': cart_sku})

            # 5. 返回,并且设置cookie
            response.set_cookie('carts', cart_data)

            return response

    def get(self, request):
        '''
        返回购物车页面
        :param request:
        :return:
        '''
        # hash:
        # 'carts_user_id':{
        #     'sku_id':count
        # }
        # # set:
        # 'selected_user_id': [sku_id1, sku_id2, ...]

        # 1.判断用户是否登录
        user = request.user
        if user.is_authenticated:
            # 2.如果登录, 链接redis
            redis_conn = get_redis_connection('carts')

            # 3.获取数据: 1. hash  2. set
            item_dict = redis_conn.hgetall('carts_%s' % user.id)
            cart_selected = redis_conn.smembers('selected_%s' % user.id)

            # 4.整理格式:  cookie中的格式
            cart_dict = {}
            for sku_id, count in item_dict.items():
                cart_dict[int(sku_id)] = {
                    'count':int(count),
                    'selected': sku_id in cart_selected
                }
        else:
            # 未登录的:
            # 1.获取cookie中的数据
            cookie_cart = request.COOKIES.get('carts')

            # 2.判断是否存在,
            if cookie_cart:
                # 如果存在, 解码
                cart_dict = pickle.loads(base64.b64decode(cookie_cart))
            else:
                # 3.不存在, 创建一个新的
                cart_dict = {}
        # 1. 获取所有的商品id
        sku_ids = cart_dict.keys()

        # 2. 把所有的商品id变为 商品  要进行查询操作
        skus = SKU.objects.filter(id__in=sku_ids)

        cart_list = []
        # 3. 遍历,获取单个商品
        for sku in skus:
            count = cart_dict.get(sku.id).get('count')
            # 4. 拼接数据: 把单个商品的所有数据放入字典中, 然后放入列表
            cart_list.append({
                'id':sku.id,
                'count':count,
                'selected':str(cart_dict.get(sku.id).get('selected')),
                'default_image_url':sku.default_image_url,
                'price':str(sku.price),
                'amount':str(sku.price * count),
                'name':sku.name
            })

        # 5. 再次拼接参数
        context = {
            'cart_skus':cart_list
        }

        # 6. 返回
        return render(request, 'cart.html', context)


    def post(self, request):
        '''
        增加购物车数据
        :param request:
        :return:
        '''
        # 1.接收参数 sku_id, count, selected
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected', True)

        # 2.校验参数: 总体 + 单个检验
        if not all([sku_id, count]):
            return http.HttpResponseForbidden('缺少必传参数')

        # 单个检验
        try:
            SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('参数sku_id有误')

        # 单个检验
        try:
            count = int(count)
        except Exception:
            return http.HttpResponseForbidden('参数count有误')

        # 单个检验
        if selected:
            if not isinstance(selected, bool):
                return http.HttpResponseForbidden('参数selected有误')

        user = request.user
        # 3. 判断是否是登录用户:
        if user.is_authenticated:
            # 登录用户
            # 4. 链接redis, 获取链接对象
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()

            # 5. 往hash表中累加数据: hash: 用户id, 商品id, count
            pl.hincrby('carts_%s' % user.id, sku_id, count)

            # 6. 往set表中增加选中商品的id
            if selected:
                # set: user.id: sku_id
                pl.sadd('selected_%s' % user.id, sku_id)
            # 执行管道:
            pl.execute()

            # 7. 返回
            return http.JsonResponse({'code':RETCODE.OK,
                                      'errmsg':'增加购物车成功'})

        else:
            # 未登录用户
            # 1. 获取以前存储的cookie值
            cookie_cart = request.COOKIES.get('carts')

            # 2. 判断以往的cookie是否存在
            if cookie_cart:
                # 3. 如果存在:  解密 ==> 得到字典
                byts = base64.b64decode(cookie_cart.encode()) # 把 base64位的bytes 转为 正常的byte类型
                cart_dict = pickle.loads(byts)  # 把 bytes 转为 字典
                # 原来的字典格式:
                # cart_dic = {
                #     'sku_id':{
                #         'count':1,
                #         'selected':True
                #     }
                # }
            else:
                # 4. 如果不存在: 生成新的字典
                cart_dict = {}

            # 5. 如果存在===> 判断当前商品的sku_id 是否在原来的cookie中:
            # 现在count+原来的count
            if sku_id in cart_dict:
                count += cart_dict.get(sku_id).get('count')

            # 6. 更新字典
            cart_dict[sku_id] = {
                'count':count,
                'selected':selected
            }

            # 7. 加密
            cart_data = base64.b64encode(pickle.dumps(cart_dict)).decode()

            # 8. 写入cookie中
            response = http.JsonResponse({'code':RETCODE.OK,
                                          'errmsg':'ok'})

            response.set_cookie('carts', cart_data)

            # 9. 返回
            return response