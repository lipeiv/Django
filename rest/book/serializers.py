# 定义序列化器（类）
from rest_framework import serializers
from .models import HeroInfo

class MyHeroInfoSerializer(serializers.Serializer):
    """英雄数据序列化器"""
    GENDER_CHOICES = (
        (0, 'male'),
        (1, 'female')
    )
    id = serializers.IntegerField(label='ID', read_only=True)
    hname = serializers.CharField(label='名字', max_length=20)


# 定义一个序列化器，来对BookInfo模型类进行序列化操作 -- 模型类对象-序列化->字典
class BookInfoSerializer(serializers.Serializer):
    """图书数据序列化器"""
    id = serializers.IntegerField(label='ID', read_only=True)
    btitle = serializers.CharField(label='名称', max_length=20)
    bpub_date = serializers.DateField(label='发布日期', required=False)
    bread = serializers.IntegerField(label='阅读量', required=False)
    bcomment = serializers.IntegerField(label='评论量', required=False)
    image = serializers.ImageField(label='图片', required=False)

    # heroinfo_set = MyHeroInfoSerializer(many=True)
    # heroinfo_set = serializers.PrimaryKeyRelatedField(many=True, queryset=HeroInfo.objects.all())
    heroinfo_set  = serializers.StringRelatedField(many=True, queryset=HeroInfo.objects.all())





class MyBookInfoSerializer(serializers.Serializer):
    btitle = serializers.CharField(label='名称', max_length=20)
    bpub_date = serializers.DateField(label='发布日期', required=False)

class HeroInfoSerializer(serializers.Serializer):
    """英雄数据序列化器"""
    GENDER_CHOICES = (
        (0, 'male'),
        (1, 'female')
    )
    id = serializers.IntegerField(label='ID', read_only=True)
    hname = serializers.CharField(label='名字', max_length=20)
    hgender = serializers.ChoiceField(choices=GENDER_CHOICES, label='性别', required=False)
    hcomment = serializers.CharField(label='描述信息', max_length=200, required=False, allow_null=True)
    # hbook = serializers.PrimaryKeyRelatedField(read_only=True)
    # hbook = serializers.StringRelatedField(read_only=True)
    hbook = BookInfoSerializer()











