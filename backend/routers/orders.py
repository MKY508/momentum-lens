"""
Order management API endpoints.
"""

from typing import Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Body
from sqlalchemy.orm import Session

from backend.models.base import get_db_dependency
from backend.models import Orders, Transactions
from backend.models.portfolio import OrderStatus, TransactionType
from backend.core.portfolio_manager import get_portfolio_manager
from backend.utils.validators import validate_orders

router = APIRouter()


@router.post("/create")
async def create_order(
    order_data: Dict = Body(...),
    user_id: int = 1,
    db: Session = Depends(get_db_dependency)
):
    """Create a new order"""
    # Validate order
    is_valid, errors = validate_orders([order_data])
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid order: {errors}")
    
    # Create order in database
    order = Orders(
        user_id=user_id,
        code=order_data['code'],
        order_type=order_data['order_type'],
        side=TransactionType.BUY if order_data['side'] == 'BUY' else TransactionType.SELL,
        quantity=order_data['quantity'],
        limit_price=order_data.get('limit_price'),
        stop_price=order_data.get('stop_price'),
        status=OrderStatus.PENDING,
        created_at=datetime.now()
    )
    
    db.add(order)
    db.commit()
    db.refresh(order)
    
    return {
        "order_id": order.id,
        "status": order.status.value,
        "message": "Order created successfully"
    }


@router.get("/list")
async def list_orders(
    user_id: int = 1,
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db_dependency)
):
    """List orders with optional status filter"""
    query = db.query(Orders).filter(Orders.user_id == user_id)
    
    if status:
        try:
            status_enum = OrderStatus[status.upper()]
            query = query.filter(Orders.status == status_enum)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    orders = query.order_by(Orders.created_at.desc()).limit(limit).all()
    
    return {
        "orders": [
            {
                "id": o.id,
                "code": o.code,
                "order_type": o.order_type,
                "side": o.side.value,
                "quantity": o.quantity,
                "limit_price": o.limit_price,
                "status": o.status.value,
                "created_at": o.created_at,
                "filled_quantity": o.filled_quantity,
                "avg_fill_price": o.avg_fill_price
            }
            for o in orders
        ]
    }


@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    user_id: int = 1,
    db: Session = Depends(get_db_dependency)
):
    """Cancel an order"""
    order = db.query(Orders).filter(
        Orders.id == order_id,
        Orders.user_id == user_id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status not in [OrderStatus.PENDING, OrderStatus.SUBMITTED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel order with status {order.status.value}"
        )
    
    order.status = OrderStatus.CANCELLED
    order.cancelled_at = datetime.now()
    db.commit()
    
    return {
        "order_id": order_id,
        "status": "CANCELLED",
        "message": "Order cancelled successfully"
    }


@router.post("/{order_id}/execute")
async def execute_order(
    order_id: int,
    execution_price: float,
    user_id: int = 1,
    db: Session = Depends(get_db_dependency)
):
    """Manually execute an order (for testing)"""
    order = db.query(Orders).filter(
        Orders.id == order_id,
        Orders.user_id == user_id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status != OrderStatus.SUBMITTED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot execute order with status {order.status.value}"
        )
    
    # Create transaction
    transaction = Transactions(
        user_id=user_id,
        code=order.code,
        action=order.side,
        price=execution_price,
        shares=order.quantity,
        amount=execution_price * order.quantity,
        commission=execution_price * order.quantity * 0.0003,  # 0.03% commission
        order_id=str(order_id),
        execution_price=execution_price,
        transaction_date=datetime.now().date(),
        transaction_time=datetime.now()
    )
    
    db.add(transaction)
    
    # Update order status
    order.status = OrderStatus.FILLED
    order.filled_quantity = order.quantity
    order.avg_fill_price = execution_price
    order.filled_at = datetime.now()
    
    db.commit()
    
    # Update holdings
    manager = get_portfolio_manager(user_id)
    manager.update_holdings(transaction)
    
    return {
        "order_id": order_id,
        "status": "FILLED",
        "execution_price": execution_price,
        "message": "Order executed successfully"
    }


@router.get("/transactions")
async def get_transactions(
    user_id: int = 1,
    limit: int = 100,
    db: Session = Depends(get_db_dependency)
):
    """Get transaction history"""
    transactions = db.query(Transactions).filter(
        Transactions.user_id == user_id
    ).order_by(Transactions.transaction_time.desc()).limit(limit).all()
    
    return {
        "transactions": [
            {
                "id": t.id,
                "code": t.code,
                "action": t.action.value,
                "price": t.price,
                "shares": t.shares,
                "amount": t.amount,
                "commission": t.commission,
                "transaction_date": t.transaction_date,
                "transaction_time": t.transaction_time
            }
            for t in transactions
        ]
    }