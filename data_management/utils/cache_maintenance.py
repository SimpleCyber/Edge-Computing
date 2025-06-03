from django.utils import timezone
from datetime import timedelta
from ..models import CachedData

def downgrade_inactive_data():
    # Downgrade frequent data that hasn't been accessed in 10 minutes
    frequent_to_downgrade = CachedData.objects.filter(
        cache_level='FREQUENT',
        last_accessed__lt=timezone.now() - timedelta(minutes=10)
    ).update(cache_level='LESS_FREQUENT')

    # Downgrade less frequent data that hasn't been accessed in 1 hour
    less_frequent_to_downgrade = CachedData.objects.filter(
        cache_level='LESS_FREQUENT',
        last_accessed__lt=timezone.now() - timedelta(hours=1)
    ).update(cache_level='RARE')

    return {
        'frequent_downgraded': frequent_to_downgrade,
        'less_frequent_downgraded': less_frequent_to_downgrade
    }