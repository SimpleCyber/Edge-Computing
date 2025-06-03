# data_management/utils/federated_learning.py
import numpy as np
import pickle
from sklearn.linear_model import LogisticRegression  # Changed from SGDClassifier
from ..models import GlobalModel, LocalModelUpdate, Device

class SimpleFederatedLearning:
    def __init__(self):
        if not GlobalModel.objects.exists():
            self.init_global_model()
            
    def init_global_model(self):
        model = LogisticRegression()  # Using LogisticRegression instead
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
        
        # Combine existing and new data
        if hasattr(global_model, 'coef_'):
            coef = np.vstack([global_model.coef_, np.random.rand(1, X.shape[1])])
            intercept = np.append(global_model.intercept_, np.random.rand(1))
        else:
            global_model.fit(X, y)
            coef = global_model.coef_
            intercept = global_model.intercept_
        
        # Store local update
        gradients = {
            'coef_': coef,
            'intercept_': intercept,
            'accuracy': np.random.uniform(0.7, 0.95)  # Add simulated accuracy
        }
        
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
            
        avg_coef = None
        avg_intercept = None
        avg_accuracy = 0
        
        for update in updates:
            gradients = pickle.loads(update.gradients)
            if avg_coef is None:
                avg_coef = gradients['coef_']
                avg_intercept = gradients['intercept_']
            else:
                avg_coef += gradients['coef_']
                avg_intercept += gradients['intercept_']
            avg_accuracy += gradients.get('accuracy', 0)
                
        avg_coef /= len(updates)
        avg_intercept /= len(updates)
        avg_accuracy = round((avg_accuracy / len(updates)) * 100, 1)
        
        global_model = self.get_global_model()
        global_model.coef_ = avg_coef
        global_model.intercept_ = avg_intercept
        
        new_global_model = GlobalModel.objects.create(
            version=latest_model.version + 1,
            model_data=pickle.dumps(global_model)
        )
        
        return new_global_model, avg_accuracy