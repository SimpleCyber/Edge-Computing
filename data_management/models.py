from django.db import models
from django.utils import timezone
from datetime import timedelta

class Device(models.Model):
    name = models.CharField(max_length=100)
    device_type = models.CharField(max_length=50)
    location = models.CharField(max_length=100)
    last_active = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        now = timezone.now()
        if not self.last_active or (now - self.last_active) > timedelta(hours=1):
            self.last_active = now
        super().save(*args, **kwargs)

class RawData(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    data = models.JSONField()  # Store sensor readings
    is_processed = models.BooleanField(default=False)

class CachedData(models.Model):
    CACHE_LEVEL_CHOICES = [
        ('FREQUENT', 'Frequent Access'),
        ('LESS_FREQUENT', 'Less Frequent Access'),
        ('RARE', 'Rarely Accessed'),
    ]
    raw_data = models.OneToOneField(RawData, on_delete=models.CASCADE)
    cache_level = models.CharField(max_length=20, choices=CACHE_LEVEL_CHOICES)
    last_accessed = models.DateTimeField(auto_now=True)
    access_count = models.PositiveIntegerField(default=0)

class DataFragment(models.Model):
    original_data = models.ForeignKey(RawData, on_delete=models.CASCADE)
    fragment_id = models.CharField(max_length=10)
    fragment_data = models.BinaryField()
    storage_node = models.CharField(max_length=100) 
    is_parity = models.BooleanField(default=False)

class GlobalModel(models.Model):
    version = models.PositiveIntegerField()
    model_data = models.BinaryField()  # Serialized ML model
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    accuracy = models.FloatField(null=True, blank=True)

class LocalModelUpdate(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    global_model = models.ForeignKey(GlobalModel, on_delete=models.CASCADE)
    gradients = models.BinaryField()  # Serialized gradients
    created_at = models.DateTimeField(auto_now_add=True)


class PerformanceMetrics(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    edge_processing_time = models.FloatField()  # in milliseconds
    cloud_processing_time = models.FloatField()  # in milliseconds (simulated)
    data_transfer_size = models.FloatField()  # in KB
    raw_storage_size = models.FloatField()  # in KB
    encoded_storage_size = models.FloatField()  # in KB