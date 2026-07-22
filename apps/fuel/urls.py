from django.urls import path
from .views import Root, RoutePlanningView

urlpatterns = [
    path("", Root.as_view(), name="root"),
    path("api/route-planning/", RoutePlanningView.as_view(), name="route-planning"),
]
