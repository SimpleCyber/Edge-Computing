# caching.py
from django.core.cache import caches
from ..models import CachedData, RawData
from django.utils import timezone
from datetime import timedelta

class HierarchicalCache:
    def __init__(self):
        self.frequent_cache = caches['frequent']
        self.less_frequent_cache = caches['less_frequent']
        self.rare_cache = caches['rare']

    def cache_data(self, raw_data_id, data):
        cached_obj, created = CachedData.objects.get_or_create(
            raw_data_id=raw_data_id,
            defaults={'cache_level': 'FREQUENT'}
        )

        if cached_obj.cache_level == 'FREQUENT':
            self.frequent_cache.set(f'data_{raw_data_id}', data, timeout=300)
        elif cached_obj.cache_level == 'LESS_FREQUENT':
            self.less_frequent_cache.set(f'data_{raw_data_id}', data, timeout=600)
        else:
            self.rare_cache.set(f'data_{raw_data_id}', data, timeout=3600)

    def get_data(self, raw_data_id):
        data = self.frequent_cache.get(f'data_{raw_data_id}')
        if data:
            self._register_hit(raw_data_id)
            self._update_cache_access(raw_data_id, 'FREQUENT')
            return data

        data = self.less_frequent_cache.get(f'data_{raw_data_id}')
        if data:
            self._register_hit(raw_data_id)
            self._update_cache_access(raw_data_id, 'LESS_FREQUENT')
            return data

        data = self.rare_cache.get(f'data_{raw_data_id}')
        if data:
            self._register_hit(raw_data_id)
            self._update_cache_access(raw_data_id, 'RARE')
            return data

        self._register_access(raw_data_id)
        return None

    def _update_cache_access(self, raw_data_id, current_level):
        try:
            cached_data = CachedData.objects.get(raw_data_id=raw_data_id)
            cached_data.last_accessed = timezone.now()

            if current_level == 'FREQUENT':
                if cached_data.access_count < 3 or (timezone.now() - cached_data.last_accessed) > timedelta(minutes=10):
                    cached_data.cache_level = 'LESS_FREQUENT'
            elif current_level == 'LESS_FREQUENT':
                if cached_data.access_count >= 3:
                    cached_data.cache_level = 'FREQUENT'
                elif (timezone.now() - cached_data.last_accessed) > timedelta(hours=1):
                    cached_data.cache_level = 'RARE'
            else:
                if cached_data.access_count >= 1:
                    cached_data.cache_level = 'LESS_FREQUENT'

            cached_data.save()
        except CachedData.DoesNotExist:
            pass

    def _register_hit(self, raw_data_id):
        try:
            obj = CachedData.objects.get(raw_data_id=raw_data_id)
            obj.access_count += 1
            obj.hit_count += 1
            obj.save()
        except CachedData.DoesNotExist:
            pass

    def _register_access(self, raw_data_id):
        try:
            obj = CachedData.objects.get(raw_data_id=raw_data_id)
            obj.access_count += 1
            obj.save()
        except CachedData.DoesNotExist:
            pass
