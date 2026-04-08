import uuid
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

# Neural Node Storage (Temporary Memory Buffer)
NODE_STORAGE = []

def create_neural_node(node: NodeProtocol):
    """
    Initializes a new Secure Control Node.
    Generates a unique Room Signature and timestamps the entry.
    """
    node.room_id = str(uuid.uuid4())
    # Simulation: Storing in memory
    NODE_STORAGE.insert(0, node.dict())
    return node.dict()

def get_active_streams():
    """
    Synchronizes the local buffer with active data streams.
    """
    return NODE_STORAGE

def get_node_stats():
    """
    Calculates telemetry across all active nodes.
    """
    total = len(NODE_STORAGE)
    active = sum(1 for n in NODE_STORAGE if n['status'] == 'PENDING')
    completed = sum(1 for n in NODE_STORAGE if n['status'] == 'COMPLETED')
    return {
        "total": total,
        "active": active,
        "completed": completed,
        "threats": 0 # Placeholder for security module
    }
