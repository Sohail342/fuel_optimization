from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.views import APIView

from apps.fuel.serializers import RoutePlanningSerializer
from apps.fuel.services.routing_service import RoutingService


class Root(APIView):
    def get(self, request):
        return HttpResponse("Docs on api/docs", content_type="text/plain")


class RoutePlanningView(APIView):
    def get(self, request):
        return self._plan(request.query_params)

    def post(self, request):
        return self._plan(request.data)

    def _plan(self, raw_data):
        serializer = RoutePlanningSerializer(data=raw_data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

        start = serializer.validated_data["start"]
        end = serializer.validated_data["end"]

        try:
            result = RoutingService().plan_trip(start=start, end=end)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=HTTP_400_BAD_REQUEST)

        return Response(result)
