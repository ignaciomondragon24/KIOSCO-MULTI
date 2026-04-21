"""
Cash Register URLs
"""
from django.urls import path
from . import views

app_name = 'cashregister'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Shifts
    path('shifts/', views.shift_list, name='shift_list'),
    path('open-shift/', views.open_shift, name='open_shift'),
    path('shift/<int:pk>/', views.shift_detail, name='shift_detail'),
    path('shift/<int:pk>/close/', views.close_shift, name='close_shift'),
    path('shift/<int:pk>/data/', views.shift_data_api, name='shift_data_api'),
    path('shift/<int:pk>/report/', views.shift_report_pdf, name='shift_report'),
    path('shift/<int:pk>/report/pdf/', views.shift_report_pdf, name='shift_report_pdf'),
    path('shift/<int:shift_pk>/movement/', views.add_movement, name='add_movement'),
    
    # Movements
    path('movements/', views.movement_list, name='movement_list'),
    
    # Cash Registers
    path('registers/', views.register_list, name='register_list'),
    path('registers/create/', views.register_create, name='register_create'),
]
