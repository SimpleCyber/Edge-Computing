import numpy as np
import pickle
from sklearn.linear_model import SGDClassifier
from ..models import GlobalModel, LocalModelUpdate, Device

class SimpleFederatedLearning:
    def __init__(self):
        # Initialize with a simple model if none exists
        if not GlobalModel.objects.exists():
            self.init_global_model()
            
    def init_global_model(self):
        model = SGDClassifier(loss='log_loss')
        # Initialize with dummy data
        X = np.random.rand(10, 5)
        y = np.random.randint(0, 2, 10)
        model.fit(X, y)
        
        global_model = GlobalModel.objects.create(
            version=1,
            model_data=pickle.dumps(model)
        )
        return global_model
        
    def get_global_model(self):
        latest_model = GlobalModel.objects.latest('version')
        return pickle.loads(latest_model.model_data)
        
    def train_local_model(self, device_id, X, y):
        device = Device.objects.get(pk=device_id)
        global_model = self.get_global_model()
        
        # Local training
        global_model.partial_fit(X, y, classes=[0, 1])
        
        # Simulate gradient computation (in reality would compute actual gradients)
        gradients = {
            'coef_': global_model.coef_,
            'intercept_': global_model.intercept_
        }
        
        # Store local update
        LocalModelUpdate.objects.create(
            device=device,
            global_model=GlobalModel.objects.latest('version'),
            gradients=pickle.dumps(gradients)
        )
        
        return gradients
        
    def aggregate_updates(self):
        latest_model = GlobalModel.objects.latest('version')
        updates = LocalModelUpdate.objects.filter(global_model=latest_model)
        
        if not updates.exists():
            return latest_model
            
        # Simple averaging of gradients
        avg_coef = None
        avg_intercept = None
        
        for update in updates:
            gradients = pickle.loads(update.gradients)
            if avg_coef is None:
                avg_coef = gradients['coef_']
                avg_intercept = gradients['intercept_']
            else:
                avg_coef += gradients['coef_']
                avg_intercept += gradients['intercept_']
                
        avg_coef /= len(updates)
        avg_intercept /= len(updates)
        
        # Update global model
        global_model = pickle.loads(latest_model.model_data)
        global_model.coef_ = avg_coef
        global_model.intercept_ = avg_intercept
        
        # Create new version
        new_global_model = GlobalModel.objects.create(
            version=latest_model.version + 1,
            model_data=pickle.dumps(global_model)
        )
        
        return new_global_model