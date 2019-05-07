from django.db import models

# Create your models here.
from django.db import models


class BookInfo(models.Model):
    btitle = models.CharField(max_length=20, verbose_name='名称')
    bpub_date = models.DateField(verbose_name='发布日期')
    bread=models.IntegerField(default=0, verbose_name='阅读量')
    bcomment = models.IntegerField(default=0, verbose_name='评论量')
    is_delete = models.BooleanField(default=0, verbose_name='逻辑删除')

    class Meta:
        db_table = 'tb_books'
        verbose_name = '图书'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.btitle


# 定义英雄模型类HeroInfo
class HeroInfo(models.Model):
    # 这个是元组是一个可选项,元组中也是元组, 其中:

    # 0, 1: 是在数据库中真实存在的值
    # 意味着hgender这个字段在数据库中存储的要么是0,要么是1

    # male, female: 用于显示在admin站点中
    # 类似于: verbose_name
    GENDER_CHOICES = (
        (0, 'male'),
        (1, 'female')
    )
    hname = models.CharField(max_length=20, verbose_name='名称')
    # 性别我们使用的是类似于枚举类型来做的:
    # choices: 可选范围,传入的是个元组类型,在上面定义的.
    hgender = models.SmallIntegerField(choices=GENDER_CHOICES, default=0, verbose_name='性别')
    hcomment = models.CharField(max_length=200, null=True, verbose_name='描述信息')
    # 利用ForeignKey这个属性指定hbook这个字段为外键.
    # 第一个参数: 表示外键关联到书籍表
    # 注意: 如果调用外键hbook的话: 返回的是book这个模型对象.
    hbook = models.ForeignKey(BookInfo, on_delete=models.CASCADE, verbose_name='图书')  # 外键
    is_delete = models.BooleanField(default=False, verbose_name='逻辑删除')

    class Meta:
        db_table = 'tb_heros'
        verbose_name = '英雄'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.hname