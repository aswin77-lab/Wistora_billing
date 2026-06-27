from django.contrib import admin
from django.urls import path
from billing import views

urlpatterns = [
    path('admin-backend/', admin.site.urls),
    
    # 1. Map both the root domain AND 'login/' to the login view
    path('', views.login_view, name='login_root'),
    path('login/', views.login_view, name='login'), # This satisfies Django's default redirector!
    
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('customers/', views.customers_view, name='customers'),
    path('invoices/', views.invoices_view, name='invoices'),
    path('payments/', views.payments_view, name='payments'),
    path('reports/', views.reports_view, name='reports'),
]