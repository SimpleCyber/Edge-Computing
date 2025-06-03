from django.core.cache import caches
from ..models import CachedData, RawData
from django.utils import timezone
import random

class HierarchicalCache:
    def __init__(self):
        self.frequent_cache = caches['frequent']
        self.less_frequent_cache = caches['less_frequent']
        self.rare_cache = caches['rare']

    def cache_data(self, raw_data_id, data):
        weights = self.generate_weight_distribution() 

        initial_level = random.choices(
            ['FREQUENT', 'LESS_FREQUENT', 'RARE'],
            weights=weights,
            k=1
        )[0]

        cached_obj, created = CachedData.objects.get_or_create(
            raw_data_id=raw_data_id,
            defaults={
                'cache_level': initial_level,
                'access_count': 0
            }
        )

        if cached_obj.cache_level == 'FREQUENT':
            self.frequent_cache.set(f'data_{raw_data_id}', data, timeout=300)
        elif cached_obj.cache_level == 'LESS_FREQUENT':
            self.less_frequent_cache.set(f'data_{raw_data_id}', data, timeout=1800)
        else:
            self.rare_cache.set(f'data_{raw_data_id}', data, timeout=3600) 

    def get_data(self, raw_data_id):
        data = self.frequent_cache.get(f'data_{raw_data_id}')
        if data:
            self._update_cache_level(raw_data_id, 'FREQUENT')
            return data

        data = self.less_frequent_cache.get(f'data_{raw_data_id}')
        if data:
            self._update_cache_level(raw_data_id, 'LESS_FREQUENT')
            return data

        data = self.rare_cache.get(f'data_{raw_data_id}')
        if data:
            self._update_cache_level(raw_data_id, 'RARE')
            return data

        return None
    
    @staticmethod
    def generate_weight_distribution():
        nums = [random.uniform(1, 100) for _ in range(3)]
        nums.sort(reverse=True)
        total = sum(nums)
        weights = [round((n / total) * 100) for n in nums]
        diff = 100 - sum(weights)
        weights[0] += diff
        return weights

    def _update_cache_level(self, raw_data_id, current_level):
        try:
            cached_data = CachedData.objects.get(raw_data_id=raw_data_id)
            cached_data.access_count += 1
            cached_data.last_accessed = timezone.now()

            if current_level == 'FREQUENT':
                pass
            elif current_level == 'LESS_FREQUENT':
                if cached_data.access_count > 3:
                    cached_data.cache_level = 'FREQUENT'
            else:  # RARE
                if cached_data.access_count > 1:
                    cached_data.cache_level = 'LESS_FREQUENT'

            cached_data.save()

            # Update caches accordingly
            data = None
            if current_level == 'FREQUENT':
                data = self.frequent_cache.get(f'data_{raw_data_id}')
            elif current_level == 'LESS_FREQUENT':
                data = self.less_frequent_cache.get(f'data_{raw_data_id}')
            else:
                data = self.rare_cache.get(f'data_{raw_data_id}')

            if data:
                if cached_data.cache_level == 'FREQUENT':
                    self.frequent_cache.set(f'data_{raw_data_id}', data, timeout=300)
                    self.less_frequent_cache.delete(f'data_{raw_data_id}')
                    self.rare_cache.delete(f'data_{raw_data_id}')
                elif cached_data.cache_level == 'LESS_FREQUENT':
                    self.less_frequent_cache.set(f'data_{raw_data_id}', data, timeout=1800)
                    self.frequent_cache.delete(f'data_{raw_data_id}')
                    self.rare_cache.delete(f'data_{raw_data_id}')
                else:
                    self.rare_cache.set(f'data_{raw_data_id}', data, timeout=3600)
                    self.frequent_cache.delete(f'data_{raw_data_id}')
                    self.less_frequent_cache.delete(f'data_{raw_data_id}')

        except CachedData.DoesNotExist:
            pass
