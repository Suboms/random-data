from django.urls import get_resolver
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView


class UrlsListView(APIView):

    def get(self, request, format=None):

        url_resolver = get_resolver()
        urlconf = url_resolver.url_patterns
        urls = {}

        def list_urls(lis, parent=""):
            for url in lis:
                if hasattr(url, "url_patterns"):
                    list_urls(url.url_patterns, parent + url.pattern.regex.pattern)
                else:
                    try:
                        name = url.name or str(url.pattern.regex.pattern)
                        url_name = reverse(name, request=request, format=format)
                        urls[name.title()] = url_name
                    except Exception:
                        pass

        list_urls(urlconf)

        return Response(urls)
