from django.http import HttpResponse
from rest_framework.views import APIView


class Root(APIView):
    def get(self, request):
        return HttpResponse("Docs on api/docs", content_type="text/plain")
