from django.db import models

class Device(models.Model):
    name = models.CharField(max_length=100)
    device_type = models.CharField(max_length=50)
    location = models.CharField(max_length=100)
    last_active = models.DateTimeField(auto_now=True)

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
    storage_node = models.CharField(max_length=100)  # Simulate different edge nodes
    is_parity = models.BooleanField(default=False)

class GlobalModel(models.Model):
    version = models.PositiveIntegerField()
    model_data = models.BinaryField()  # Serialized ML model
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class LocalModelUpdate(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    global_model = models.ForeignKey(GlobalModel, on_delete=models.CASCADE)
    gradients = models.BinaryField()  # Serialized gradients
    created_at = models.DateTimeField(auto_now_add=True)