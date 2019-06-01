from django import http
from django.core.paginator import Paginator, EmptyPage
from django.shortcuts import render

# Create your views here.
from django.utils import timezone
from django.views import View
import logging
logger = logging.getLogger('dajngo')

from goods.models import GoodsCategory, SKU, GoodsVisitCount
from goods.utils import get_categories, get_breadcrumb, get_goods_and_spec
from meiduo_mall.utils.response_code import RETCODE
import datetime


class DetailVisitView(View):

    def post(self, request, category_id):
        '''
        记录商品访问量
        :param request:
        :param category_id:
        :return:
        '''

        # 1. 根据 category_id 从 GoodsCategory 获取对应的商品类型
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return http.HttpResponseForbidden('对应的商品类型不存在')

        # 2. 创建当前时间
        t = timezone.localtime()

        today_str = '%d-%02d-%02d' %  (t.year, t.month, t.day)

        today_date = datetime.datetime.strptime(today_str, '%Y-%m-%d')


        try:
            # 3. 根据时间 获取以及存在的记录
            counts_data = category.goodsvisitcount_set.get(date=today_date)

        except GoodsVisitCount.DoesNotExist:
            # 4. 如果不存在记录, 新建一个
            counts_data = GoodsVisitCount()

        # 5. 更改
        try:
            counts_data.category = category
            counts_data.count += 1
            counts_data.save()
        except Exception as e:
            logger.error(e)
            return http.HttpResponseForbidden('更新失败')

        # 6. 返回
        return http.JsonResponse({'code':RETCODE.OK,
                                  'errmsg':'ok'})



class DetailView(View):

    def get(self, request, sku_id):
        '''
        返回详情页面
        :param reqeust:
        :param sku_id:
        :return:
        '''
        categories = get_categories()

        data = get_goods_and_spec(sku_id, request)

        context = {
            'categories':categories,
            'sku':data.get('sku'),
            'goods':data.get('goods'),
            'specs':data.get('goods_specs')
        }

        return render(request, 'detail.html', context)



class HotGoodsView(View):

    def get(self, request, category_id):

        # 1. 根据category_id(类别id),获取商品:  排序(销量) + 切片
        skus = SKU.objects.filter(category_id=category_id,
                           is_launched=True).order_by('-sales')[:2]

        hot_skus = []
        # 2. 遍历商品, 获取每一个===> 拼接成字典 ===> 放到列表 ===> json
        for sku in skus:
            hot_skus.append({
                'id':sku.id,
                'default_image_url':sku.default_image_url,
                'name':sku.name,
                'price':sku.price
            })

        # 3. 返回
        return http.JsonResponse({'code':RETCODE.OK,
                                  'errmsg':'ok',
                                  'hot_skus':hot_skus})




class ListView(View):

    def get(self, request, category_id, page_num):
        '''
        展示列表页面:
        :param request:
        :param category_id:
        :param page_num:
        :return:
        '''
        # 1. 校验:category_id
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return http.HttpResponseNotFound('goodscategory 不存在')

        # 2. 获取商品频道
        categories = get_categories()

        # 3. 面包屑效果三级展示
        breadcrumb = get_breadcrumb(category)

        # 增加的内容:
        # 1.1 获取排序方式: 查询字符串
        sort = request.GET.get('sort', 'default')

        # 1.2 判断排序方式, 确定排序依据
        if sort == 'price':
            sortkind = 'price'
        elif sort == 'hot':
            sortkind = '-sales'
        else:
            sort = 'default'
            sortkind = 'create_time'

        # 1.3 获取所有商品,并且排序
        skus = SKU.objects.filter(category=category, is_launched=True).order_by(sortkind)


        # 1.4 创建一个分页器对象
        paginator = Paginator(skus, 5)

        # 1.5 获取对应页面的商品
        try:
            page_skus = paginator.page(page_num)
        except EmptyPage:
            return http.HttpResponseNotFound('empty page')

        # 1.6 获取总计的页数
        total_page = paginator.num_pages

        # 4. 拼接数据
        context = {
            'categories':categories,
            'breadcrumb':breadcrumb,
            'total_page':total_page,
            'page_skus':page_skus,
            'page_num':page_num,
            'sort':sort,
            'category': category,  # 第三级分类
        }

        # 5. 返回
        return render(request, 'list.html', context=context)