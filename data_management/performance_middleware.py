# performance_middleware.py
import time
from .models import PerformanceMetrics
import random

class PerformanceTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        processing_time = (time.time() - start_time) * 1000  # ms
        
        # Simulate cloud processing time (2-3x slower)
        cloud_processing_time = processing_time * random.uniform(2.0, 3.0)
        
        # Estimate data size (simplified)
        data_size = len(str(request.body)) / 1024  # KB
        
        PerformanceMetrics.objects.create(
            edge_processing_time=processing_time,
            cloud_processing_time=cloud_processing_time,
            data_transfer_size=data_size,
            raw_storage_size=data_size,
            encoded_storage_size=data_size * 0.5 
        )
        
        return response