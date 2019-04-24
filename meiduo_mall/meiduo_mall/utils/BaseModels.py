from django.db import models

class BaseModel(models.Model):

    # auto_now_add=True: 当前时间会随着创建自动生成
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    update_time = models.DateTimeField(auto_now=True, verbose_name='修改时间')

    class Meta:
        # 是否为抽象类: 数据迁移的时候不会生成表
        abstract = True
