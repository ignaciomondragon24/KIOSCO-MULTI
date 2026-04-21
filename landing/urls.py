"""
URLs publicas de la landing comercial.
"""
from django.urls import path

from . import views

app_name = 'landing'

urlpatterns = [
    path('', views.home, name='home'),
]
