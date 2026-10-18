from django.urls import path

from . import views

app_name = 'borrow'

urlpatterns = [
    path('', views.index, name='index'),
]
