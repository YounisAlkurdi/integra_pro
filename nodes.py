import uuid
import json
import os
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional

class NodeProtocol(BaseModel):
    candidate_name: str
    candidate_email: Optional[str] = None
    position: str
    questions: List[str]
    scheduled_at: str
    room_id: Optional[str] = None
    status: str = "PENDING"

# Neural Node Storage (Persistent Buffer)
BUFFER_FILE = "nodes_buffer.json"

def load_buffer():
    if not os.path.exists(BUFFER_FILE):
        return []
    try:
        with open(BUFFER_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_buffer(data):
    with open(BUFFER_FILE, "w") as f:
        json.dump(data, f, indent=4)

NODE_STORAGE = load_buffer()

def create_neural_node(node: NodeProtocol):
    """
    Initializes a new Secure Control Node.
    Generates a unique Room Signature and timestamps the entry.
    """
    node.room_id = str(uuid.uuid4())
    data = node.dict()
    
    global NODE_STORAGE
    NODE_STORAGE.insert(0, data)
    save_buffer(NODE_STORAGE)
    
    return data

def get_active_streams():
    """
    Synchronizes the local buffer with active data streams.
    """
    return load_buffer() # Always reload to get fresh data from disk

def delete_node(room_id: str):
    """
    Purges a node from the neural buffer.
    """
    global NODE_STORAGE
    NODE_STORAGE = [n for n in NODE_STORAGE if n['room_id'] != room_id]
    save_buffer(NODE_STORAGE)
    return True

def get_node_stats():
    """
    Calculates telemetry across all active nodes.
    """
    nodes = load_buffer()
    total = len(nodes)
    active = sum(1 for n in nodes if n['status'] == 'PENDING')
    completed = sum(1 for n in nodes if n['status'] == 'COMPLETED')
    return {
        "total": total,
        "active": active,
        "completed": completed,
        "threats": 0 
    }
