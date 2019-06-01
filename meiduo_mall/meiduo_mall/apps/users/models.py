from django.contrib.auth.models import AbstractUser
from django.db import models
from itsdangerous import TimedJSONWebSignatureSerializer
from django.conf import settings
from itsdangerous import BadData

# Create your models here.
from meiduo_mall.utils.BaseModel import BaseModel


class User(AbstractUser):

    # 增加一个mobile字段:
    mobile = models.CharField(max_length=11, verbose_name='手机号')

    # 新增一个字段: 用于记录邮箱是否验证过:
    email_active = models.BooleanField(default=False, verbose_name='邮箱是否验证')

    # 增加默认地址字段:
    default_address = models.ForeignKey('Address', on_delete=models.SET_NULL,
                                        null=True,
                                        blank=True,
                                        related_name='users',
                                        verbose_name='默认地址')


    class Meta:
        db_table = 'tb_users'
        verbose_name = '用户'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.username


    def generate_verify_email_token(self):
        '''
        生成token的一个函数:
        :return:
        '''
        serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY,
                                        expires_in= 3600 * 24)

        data = {
            'user_id':self.id,
            'email':self.email
        }

        token = serializer.dumps(data).decode()

        verify_url = settings.EMAIL_VERIFY_URL + '?token=' + token

        return verify_url

    @staticmethod
    def check_verify_email_token(token):
        '''
           解密token的一个函数:
           :return:
       '''
        serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY,
                                                     expires_in=3600 * 24)

        try:
            data = serializer.loads(token)
        except BadData:
            return None

        else:
            user_id = data.get('user_id')
            email = data.get('email')

        try:
            user = User.objects.get(id=user_id, email=email)
        except User.DoesNotExist:
            return None

        else:
            return user


class Address(BaseModel):

    user = models.ForeignKey(User,
                             on_delete=models.CASCADE,
                             related_name='addresses',
                             verbose_name='用户')

    province = models.ForeignKey('areas.Area',
                                 on_delete=models.PROTECT,
                                 related_name='province_addresses',
                                 verbose_name='省')

    city = models.ForeignKey('areas.Area',
                                 on_delete=models.PROTECT,
                                 related_name='city_addresses',
                                 verbose_name='市')

    district = models.ForeignKey('areas.Area',
                                 on_delete=models.PROTECT,
                                 related_name='district_addresses',
                                 verbose_name='区')

    title = models.CharField(max_length=20, verbose_name='标题')

    receiver = models.CharField(max_length=20, verbose_name='收货人')

    place = models.CharField(max_length=30, verbose_name='地址')

    mobile = models.CharField(max_length=11, verbose_name='手机号')

    tel = models.CharField(max_length=20, verbose_name='固定电话',
                           null=True, blank=True, default='')

    email = models.CharField(max_length=20, verbose_name='邮箱',
                           null=True, blank=True, default='')

    is_deleted = models.BooleanField(default=False, verbose_name='逻辑删除')

    class Meta:
        db_table = 'tb_address'
        verbose_name = '用户地址'
        verbose_name_plural = verbose_name
        ordering = ['-update_time']
