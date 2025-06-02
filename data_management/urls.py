from django.urls import path
from .views import DashboardView, SimulateDeviceView, ProcessDataView, AutoGenerateAPI

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('simulate/', SimulateDeviceView.as_view(), name='simulate_device'),
    path('process/', ProcessDataView.as_view(), name='process_data'),
    path('api/generate-data/', AutoGenerateAPI.as_view(), name='generate_data_api'),
]