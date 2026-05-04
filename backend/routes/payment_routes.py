from fastapi import APIRouter, Depends, Request
from ..auth import get_current_user
from ..payments import PaymentRequest, execute_payment, handle_stripe_webhook
from ..utils import get_env_safe

router = APIRouter(tags=["Payments"])

@router.get("/config")
async def get_config():
    """Stripe Config Distributor."""
    pk = get_env_safe("STRIPE_PUBLISHABLE_KEY")
    return {"publishableKey": pk}

@router.post("/create-payment-intent")
async def create_payment_intent(payment_req: PaymentRequest, request: Request, user: dict = Depends(get_current_user)):
    """Stripe Transaction Node."""
    return await execute_payment(payment_req, request, user["sub"])

@router.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Stripe Cloud Event Handshake."""
    return await handle_stripe_webhook(request)
