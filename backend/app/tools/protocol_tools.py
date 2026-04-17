from langchain_core.tools import tool
import json
from ..core.nodes import create_neural_node, delete_node, get_node_stats, NodeProtocol
from ..core.mailer import send_interview_invitation

@tool
def execute_establish_secure_link(candidate_name: str, position: str, user_id: str, candidate_email: str = None, scheduled_at: str = None, questions: list[str] = None) -> str:
    """
    Initialize a secure interview node session.
    Use this when requested to set up an interview.
    """
    try:
        # In a real async environment with LangChain, we'd use async tool
        # but for this bridge, we'll wrap the async call if needed or use a runner
        import asyncio
        loop = asyncio.get_event_loop()
        node = NodeProtocol(
            candidate_name=candidate_name,
            candidate_email=candidate_email,
            position=position,
            questions=questions or ["Identify your core strengths.", "Explain your approach to complex system architecture."],
            scheduled_at=scheduled_at or ""
        )
        res = loop.run_until_complete(create_neural_node(node, str(user_id)))
        return f"NEURAL LINK ACTIVE: {json.dumps(res)} [INTEGRA_SYSTEM_EVENT: {{\"event\": \"node-created\"}}]"
    except Exception as e:
        return f"CRITICAL_FAILURE: Protocol corruption. Error: {str(e)}"

@tool
def execute_transmit_invitation(candidate_name: str, candidate_email: str, scheduled_at: str, room_id: str) -> str:
    """
    Dispatch an interview invitation email to the candidate.
    """
    try:
        import os
        domain = os.getenv("APP_DOMAIN", "https://tist-integra.vercel.app")
        room_link = f"{domain}/integra-session.html?room={room_id}&role=candidate"
        res = send_interview_invitation(candidate_name, candidate_email, scheduled_at, room_link)
        return f"TRANSMISSION SUCCESS: {json.dumps(res)}"
    except Exception as e:
        return f"CRITICAL_FAILURE: Transmission failed. Error: {str(e)}"

@tool
def get_neural_telemetry(user_id: str) -> str:
    """Retrieve system stats for a user_id."""
    import asyncio
    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(get_node_stats(str(user_id)))
    return json.dumps(res)

@tool
def execute_purge_protocol(room_id: str, user_id: str) -> str:
    """Terminate and purge an active interview node session."""
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        success = loop.run_until_complete(delete_node(room_id))
        if success:
            return f"NEURAL LINK TERMINATED [INTEGRA_SYSTEM_EVENT: {{\"event\": \"node-deleted\"}}]"
        return "Error: Termination Signal Failed."
    except Exception as e:
        return f"CRITICAL_FAILURE: Purge aborted. Error: {str(e)}"

PROTOCOL_TOOLS = [
    execute_establish_secure_link,
    execute_transmit_invitation,
    get_neural_telemetry,
    execute_purge_protocol
]
