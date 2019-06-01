from django.shortcuts import render

# Create your views here.
from django.views import View
from django import http
from areas.models import Area
from meiduo_mall.utils.response_code import RETCODE
import logging
logger = logging.getLogger('django')
from django.core.cache import cache

class SubAreasView(View):

    def get(self, request, pk):
        '''
        返回 市区数据
        :param request:
        :param pk:
        :return:
        '''
        sub_data = cache.get('sub_data_' + pk)
        if not sub_data:

            try:
                # 1. 获取市区的数据
                sub_model_list = Area.objects.filter(parent=pk)

                # 2. 获取省级数据
                province_model = Area.objects.get(id=pk)
                # province_model = Area.objects.get(pk=pk)

                # 3. 数据处理
                sub_list = []

                for sub_model in sub_model_list:
                    sub_list.append({
                        'id': sub_model.id,
                        'name': sub_model.name
                    })

                sub_data = {
                    'id': province_model.id,
                    'name': province_model.name,
                    'subs': sub_list
                }

                cache.set('sub_data_' + pk, sub_data, 3600)
            except Exception as e:
                logger.error(e)
                return http.JsonResponse({'code':RETCODE.DBERR,
                                          'errmsg':'获取市区数据出错'})

        # 4. 返回
        return http.JsonResponse({'code':RETCODE.OK,
                                  'errmsg':'ok',
                                  'sub_data':sub_data})






class ProvinceAreasView(View):

    def get(self, request):
        '''
        返回 省份的数据
        :param request:
        :return:
        '''
        province_list = cache.get('province_list')
        if not province_list:

            try:
                province_model_list = Area.objects.filter(parent__isnull=True)

                province_list = []

                for province_model in province_model_list:
                    province_list.append({
                        'id': province_model.id,
                        'name': province_model.name
                    })

                # 进行缓存处理:
                cache.set('provine_list', province_list, 3600)

            except Exception as e:
                return http.JsonResponse({'code':RETCODE.DBERR,
                                          'errmsg':'从数据库查询省份出错'})

        return http.JsonResponse({'code':RETCODE.OK,
                                  'errmsg':'ok',
                                  'province_list':province_list})

