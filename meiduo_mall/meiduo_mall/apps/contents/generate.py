from contents.models import ContentCategory
from goods.utils import get_categories
from django.template import loader
import os
from django.conf import  settings

def generate_static_index_html():
    """
    生成静态的主页html文件
    """
    # 1. 获取分类的三级数据
    categiries = get_categories()

    # 2. 获取所有的广告分类
    content_categories = ContentCategory.objects.all()

    # 5. 组织数据
    dict = {}

    # 3. 遍历所有的广告分类, 获取每一个分类
    for cat in content_categories:
        # 4. 根据分类获取广告内容(展示的)
        dict[cat.key] = cat.content_set.filter(status=True).order_by('sequence')

    context = {
        'categories': categiries,
        'contents': dict
    }

    template = loader.get_template('index.html')

    html_text = template.render(context)

    file_path = os.path.join(settings.STATICFILES_DIRS[0], 'index.html')

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html_text)


