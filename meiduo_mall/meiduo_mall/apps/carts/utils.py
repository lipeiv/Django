import base64
import pickle
from django_redis import get_redis_connection


def merge_cart_cookie_to_redis(request, response):
    # cookie === > dict ===> redis(hash + set)

    # 1. 获取cookie中的值
    cookie_cart = request.COOKIES.get('carts')

    # 2. 判断是否存在, 不存在返回
    if not cookie_cart:
        return response

    # 3. 存在: 解密 ==> dict
    cart_dict = pickle.loads(base64.b64decode(cookie_cart))

    # 4. 整理dict的格式 ==> new_dict + new_add + new_remove
    new_dict = {}
    new_add = []
    new_remove = []
    for sku_id, item in cart_dict.items():
        new_dict[sku_id] = item['count']

        if item['selected']:
            new_add.append(sku_id)
        else:
            new_remove.append(sku_id)

    # 5. 链接redis
    redis_conn = get_redis_connection('carts')

    # 6. hash:  hmset(key, filed, value, fileds, value, ...)
    redis_conn.hmset('carts_%s' % request.user.id, new_dict)

    # 7. set: 判断new_add中是否有值, 有值: set增加
    if new_add:
        redis_conn.sadd('selected_%s' % request.user.id, *new_add)

    # 8. set: 判断new_remove中是否有值, 有值: set删除
    if new_remove:
        redis_conn.srem('selected_%s' % request.user.id, *new_remove)

    # 9. 删除cookie
    response.delete_cookie('carts')

    # 10. 返回
    return response