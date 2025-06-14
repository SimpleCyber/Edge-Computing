import numpy as np
from typing import List, Tuple
import json
import base64
from ..models import DataFragment, RawData

class ReedSolomonEC:
    def __init__(self, k: int = 4, m: int = 2):
        self.k = k  # data fragments
        self.m = m  # parity fragments
        
    def encode(self, data: bytes) -> List[Tuple[str, bytes]]:
        # Split data into k chunks
        chunk_size = (len(data) + self.k - 1) // self.k
        padded_data = data.ljust(chunk_size * self.k, b'\0')
        chunks = [padded_data[i*chunk_size:(i+1)*chunk_size] for i in range(self.k)]
        
        # Convert to numpy array for matrix operations
        data_matrix = np.array([list(chunk) for chunk in chunks], dtype=np.uint8)
        
        # Generate Vandermonde matrix for encoding
        vandermonde = np.vander(np.arange(1, self.k + self.m + 1), self.k, increasing=True)
        encoded_matrix = np.dot(vandermonde, data_matrix) % 256
        
        # Convert back to bytes
        fragments = []
        for i, row in enumerate(encoded_matrix):
            fragment_id = f"F{i+1}"
            fragment_data = bytes(row)
            fragments.append((fragment_id, fragment_data))
            
        return fragments
        
    def decode(self, fragments: List[Tuple[str, bytes]]) -> bytes:
        # We need at least k fragments
        if len(fragments) < self.k:
            raise ValueError(f"Need at least {self.k} fragments for decoding")
            
        # Sort fragments by ID
        fragments.sort()
        
        # Reconstruct original data
        fragment_ids = [int(fid[1:]) for fid, _ in fragments[:self.k]]
        fragment_data = [np.array(list(data), dtype=np.uint8) for _, data in fragments[:self.k]]
        
        # Create decoding matrix
        decoding_matrix = np.vander(fragment_ids, self.k, increasing=True)
        inv_decoding_matrix = np.linalg.inv(decoding_matrix).astype(np.uint8)
        
        # Decode original chunks
        original_chunks = np.dot(inv_decoding_matrix, fragment_data) % 256
        
        # Combine chunks and remove padding
        original_data = b''.join(bytes(chunk) for chunk in original_chunks)
        return original_data.rstrip(b'\0')

def store_with_ec(raw_data_id):
    raw_data = RawData.objects.get(pk=raw_data_id)
    
    # Convert data to JSON and then to bytes for more reliable encoding
    try:
        if isinstance(raw_data.data, str):
            # If it's already a string, parse it first to ensure valid JSON
            data_obj = json.loads(raw_data.data)
        else:
            data_obj = raw_data.data
        
        data_bytes = json.dumps(data_obj).encode('utf-8')
    except (TypeError, json.JSONDecodeError):
        # Fallback to string representation if not JSON serializable
        data_bytes = str(raw_data.data).encode('utf-8')
    
    original_size = len(data_bytes)
    
    ec = ReedSolomonEC(k=4, m=2)
    fragments = ec.encode(data_bytes)
    
    total_fragment_size = 0
    for i, (fragment_id, fragment_data) in enumerate(fragments):
        total_fragment_size += len(fragment_data)
        DataFragment.objects.create(
            original_data=raw_data,
            fragment_id=fragment_id,
            fragment_data=fragment_data,
            storage_node=f"edge_node_{i%3}",
            is_parity=(i >= 4)
        )
        
    # Calculate and store storage efficiency
    efficiency = (original_size / total_fragment_size) * 100
    return efficiency

def recover_data(raw_data_id):
    fragments = list(DataFragment.objects.filter(original_data_id=raw_data_id))
    
    if not fragments:
        return None
        
    # Get fragment data as (id, data) tuples
    fragment_data = [(f.fragment_id, f.fragment_data) for f in fragments]
    
    ec = ReedSolomonEC(k=4, m=2)
    try:
        recovered_bytes = ec.decode(fragment_data)
        
        # First try to decode as JSON
        try:
            recovered_str = recovered_bytes.decode('utf-8')
            return json.loads(recovered_str)
        except (UnicodeDecodeError, json.JSONDecodeError):
            # If not valid JSON, return as base64 encoded string
            return {
                'binary_data': base64.b64encode(recovered_bytes).decode('ascii'),
                'message': 'Data recovered but not in UTF-8 format, returned as base64'
            }
            
    except ValueError as e:
        print(f"Recovery failed: {str(e)}")
        return {
            'error': str(e),
            'message': 'Data recovery failed'
        }