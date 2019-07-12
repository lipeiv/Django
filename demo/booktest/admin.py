from django.contrib import admin

# Register your models here.
from booktest.models import HeroInfo, BookInfo

admin.site.site_header = '图书管理'
admin.site.site_title = "图书管理系统"
admin.site.index_title = '欢迎使用图书管理系统'


class HeroInfoStackInline(admin.StackedInline):
    model = HeroInfo
    extra = 1


# 创建一个admin管理站点类
class BookInfoAdmin(admin.ModelAdmin):
    list_per_page = 5
    list_display = ['btitle', 'id', 'bread']
    # fieldsets = ( )
    inlines = [HeroInfoStackInline]


class HeroInfoAdmin(admin.ModelAdmin):
    list_per_page = 5
    list_display = ['id', 'hname', 'hgender', 'hcomment']
    list_filter = ['hgender', 'hname']
    search_fields = ['hanme']

    fields = ['hname', 'hcomment']

admin.site.register(BookInfo, BookInfoAdmin)
admin.site.register(HeroInfo, HeroInfoAdmin)

