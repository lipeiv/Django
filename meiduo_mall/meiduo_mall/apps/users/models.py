from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.
class User(AbstractUser):

    # 增加一个mobile字段:
    mobile = models.CharField(max_length=11, verbose_name='手机号')

    # 增加一个字段，用于记录客户邮箱是否验证过
    emai_active = models.BooleanField(default=False, verbose_name='邮箱是否激活')


    class Meta:
        db_table = 'tb_users'
        verbose_name = '用户'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.username