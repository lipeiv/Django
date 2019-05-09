from django.shortcuts import render
from django.views import View

from contents.models import ContentCategory
from goods.utils import get_categories


class IndexView(View):

    def get(self, request):

        categiries = get_categories()

        content_categories = ContentCategory.objects.all()

        dict = {}

        for cat in content_categories:
            dict[cat.key] = cat.content_set.filter(status=True).order_by('sequence')

        context = {
            'categories': categiries,
            'contents': dict
        }
        return render(request, 'index.html', context=context)
