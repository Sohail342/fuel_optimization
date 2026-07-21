from django.urls import path
from .views import Root

urlpatterns = [
    path("", Root.as_view(), name="root"),
]
