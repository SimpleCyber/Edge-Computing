from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import random
import time
import numpy as np
from datetime import datetime
from .models import Device, RawData, CachedData, DataFragment, GlobalModel, LocalModelUpdate

# First define the base View classes to avoid circular imports

# Create dummy devices if none exist
if not Device.objects.exists():
    Device.objects.create(name="Temperature Sensor 1", device_type="Temperature", location="Room 101")
    Device.objects.create(name="Humidity Sensor 1", device_type="Humidity", location="Room 102")
    Device.objects.create(name="Multi Sensor 1", device_type="Multi", location="Hallway")

class DashboardView(View):
    def get(self, request):
        
        devices = Device.objects.all()
        raw_data_count = RawData.objects.count()

         # Calculate caching statistics with percentages
        frequent = CachedData.objects.filter(cache_level='FREQUENT').count()
        less_frequent = CachedData.objects.filter(cache_level='LESS_FREQUENT').count()
        rare = CachedData.objects.filter(cache_level='RARE').count()
        total_cached = frequent + less_frequent + rare
        
        cached_data_stats = {
            'frequent': frequent,
            'less_frequent': less_frequent,
            'rare': rare,
            'frequent_percent': round(frequent/total_cached*100, 1) if total_cached else 0,
            'less_frequent_percent': round(less_frequent/total_cached*100, 1) if total_cached else 0,
            'rare_percent': round(rare/total_cached*100, 1) if total_cached else 0,
            'hit_rate': 85  # Simulated cache hit rate percentage
        }
        
        # Calculate EC statistics
        data_nodes = DataFragment.objects.filter(is_parity=False).count()
        parity_nodes = DataFragment.objects.filter(is_parity=True).count()
        total_fragments = data_nodes + parity_nodes
        
        ec_stats = {
            'total_fragments': total_fragments,
            'data_nodes': data_nodes,
            'parity_nodes': parity_nodes,
            'data_percent': round(data_nodes/total_fragments*100, 1) if total_fragments else 0,
            'parity_percent': round(parity_nodes/total_fragments*100, 1) if total_fragments else 0,
            'efficiency': round(data_nodes/(data_nodes+parity_nodes)*100, 1) if total_fragments else 0,
            'redundancy': round((data_nodes+parity_nodes)/data_nodes, 1) if data_nodes else 0
        }
        
        cached_data_stats = {
            'frequent': CachedData.objects.filter(cache_level='FREQUENT').count(),
            'less_frequent': CachedData.objects.filter(cache_level='LESS_FREQUENT').count(),
            'rare': CachedData.objects.filter(cache_level='RARE').count(),
        }
        
        try:
            global_model = GlobalModel.objects.latest('version')
            model_updates = global_model.localmodelupdate_set.count()
        except GlobalModel.DoesNotExist:
            global_model = None
            model_updates = 0
            
        ec_stats = {
            'total_fragments': DataFragment.objects.count(),
            'data_nodes': DataFragment.objects.filter(is_parity=False).count(),
            'parity_nodes': DataFragment.objects.filter(is_parity=True).count(),
        }
        
        context = {
            'devices': devices,
            'raw_data_count': raw_data_count,
            'cached_data_stats': cached_data_stats,
            'global_model': global_model,
            'model_updates': model_updates,
            'ec_stats': ec_stats,
        }
        
        return render(request, 'data_management/dashboard.html', context)

class ProcessDataView(View):
    def get(self, request):
        fl = SimpleFederatedLearning()
        new_model = fl.aggregate_updates()
        
        raw_data = RawData.objects.filter(is_processed=True).first()
        if raw_data:
            recovered = recover_data(raw_data.id)
        
        return redirect('dashboard')

# Then import utility functions after the View classes are defined
from .utils.caching import HierarchicalCache
from .utils.erasure_coding import store_with_ec, recover_data
from .utils.federated_learning import SimpleFederatedLearning

class SimulateDeviceView(View):
    def get(self, request):
        devices = Device.objects.all()
        return render(request, 'data_management/device_input.html', {
            'devices': devices,
            'auto_generate': request.GET.get('auto') == 'true'
        })
        
    def post(self, request):
        device_id = request.POST.get('device_id')
        data_type = request.POST.get('data_type')
        auto_generate = request.POST.get('auto_generate') == 'on'
        num_records = int(request.POST.get('num_records', 10))
        
        if auto_generate:
            return self.auto_generate_data(device_id, num_records)
        else:
            return self.manual_generate_data(device_id, data_type)
    


class SimulateDeviceView(View):
    def get(self, request):
        devices = Device.objects.all()
        recent_data = RawData.objects.select_related('device').order_by('-timestamp')[:20]  # Last 20 records
        
        return render(request, 'data_management/device_input.html', {
            'devices': devices,
            'recent_data': recent_data,
            'auto_generate': request.GET.get('auto') == 'true'
        })
        
    def post(self, request):
        device_id = request.POST.get('device_id')
        data_type = request.POST.get('data_type')
        auto_generate = request.POST.get('auto_generate') == 'on'
        num_records = int(request.POST.get('num_records', 10))
        
        if auto_generate:
            return self.auto_generate_data(device_id, num_records)
        else:
            return self.manual_generate_data(device_id, data_type)
    
    def manual_generate_data(self, device_id, data_type):
        data = self.generate_single_data_point(data_type)
        return self.store_and_process(device_id, data)
    
    def auto_generate_data(self, device_id, num_records):
        # Generate multiple records with random data types
        data_types = ['temperature', 'humidity', 'pressure', 'random']
        for _ in range(num_records):
            data_type = random.choice(data_types)
            data = self.generate_single_data_point(data_type)
            self.store_and_process(device_id, data)
            time.sleep(0.1)  # Small delay between records
            
        return redirect('dashboard')
    
    def generate_single_data_point(self, data_type):
        if data_type == 'temperature':
            value = round(random.uniform(15.0, 35.0), 2)
            unit = '°C'
        elif data_type == 'humidity':
            value = random.randint(30, 90)
            unit = '%'
        elif data_type == 'pressure':
            value = random.randint(980, 1040)
            unit = 'hPa'
        else:  # random
            value = round(random.random(), 4)
            unit = 'unit'
            
        return {
            'type': data_type,
            'value': value,
            'timestamp': datetime.now().isoformat(),
            'unit': unit
        }
    
    def store_and_process(self, device_id, data):
        # Store raw data
        device = Device.objects.get(pk=device_id)
        raw_data = RawData.objects.create(
            device=device,
            data=data
        )
        
        # Process through our system
        self.process_data(raw_data.id)
        
    def process_data(self, raw_data_id):
        # 1. Caching
        cache = HierarchicalCache()
        raw_data = RawData.objects.get(pk=raw_data_id)
        cache.cache_data(raw_data_id, raw_data.data)
        
        # 2. Erasure Coding
        store_with_ec(raw_data_id)
        
        # 3. Federated Learning (simplified)
        fl = SimpleFederatedLearning()
        X = np.array([[random.random() for _ in range(5)]])
        y = np.array([random.randint(0, 1)])
        fl.train_local_model(raw_data.device.id, X, y)
        
        # Mark as processed
        raw_data.is_processed = True
        raw_data.save()


        
@method_decorator(csrf_exempt, name='dispatch')
class AutoGenerateAPI(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            device_id = data.get('device_id')
            
            if not device_id:
                return JsonResponse({'status': 'error', 'message': 'device_id is required'}, status=400)
                
            num_records = int(data.get('num_records', 10))
            
            # Verify device exists
            try:
                device = Device.objects.get(pk=device_id)
            except Device.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Device not found'}, status=404)
            
            view = SimulateDeviceView()
            view.auto_generate_data(device_id, num_records)
            
            return JsonResponse({
                'status': 'success', 
                'message': f'{num_records} records generated for device {device.name}'
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        





class ProcessDataView(View):
    def get(self, request):
        processes = []
        
        # 1. Federated Learning Aggregation
        processes.append("Starting Federated Learning aggregation...")
        fl = SimpleFederatedLearning()
        new_model = fl.aggregate_updates()
        processes.append("Federated Learning completed - new global model version {}".format(new_model.version))
        
        # 2. Data Recovery Example
        raw_data = RawData.objects.filter(is_processed=True).first()
        if raw_data:
            processes.append("Attempting data recovery for record ID {}...".format(raw_data.id))
            recovered = recover_data(raw_data.id)
            if recovered:
                processes.append("Data recovery successful")
            else:
                processes.append("Data recovery failed")
        
        return JsonResponse({
            'status': 'success',
            'processes': processes
        })
    

# Federated Learning Aggregation:

# Collects all local model updates from edge devices

# Averages the gradients to create a new global model

# Stores the updated global model with an incremented version number

# Data Recovery Example (if processed data exists):

# Attempts to recover data using erasure coding fragments

# Demonstrates the fault tolerance capability of the system