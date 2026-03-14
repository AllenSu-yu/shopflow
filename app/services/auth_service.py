from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import timedelta
from app.models.user import User, Customer
from app.utils.auth_utils import hash_password, verify_password, create_access_token
from app.utils.validators import CustomerRegister, CustomerLogin, AdminLogin
import logging

logger = logging.getLogger(__name__)


def register_customer(db: Session, customer_data: CustomerRegister) -> dict:
    """註冊新客戶"""
    # 檢查 email 是否已存在
    existing_customer = db.query(Customer).filter(Customer.email == customer_data.email).first()
    if existing_customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="該電子郵件已被註冊"
        )
    
    # 建立新客戶
    hashed_password = hash_password(customer_data.password)
    new_customer = Customer(
        email=customer_data.email,
        password_hash=hashed_password,
        name=customer_data.name,
        phone=customer_data.phone,
        address=customer_data.address
    )
    
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    
    logger.info(f"新客戶註冊成功：{new_customer.email}")
    
    # 生成 Token
    access_token = create_access_token(
        data={"sub": new_customer.id, "type": "customer"}
    )
    
    return {
        "message": "註冊成功",
        "customer": {
            "id": new_customer.id,
            "email": new_customer.email,
            "name": new_customer.name
        },
        "access_token": access_token,
        "token_type": "bearer"
    }


def authenticate_customer(db: Session, login_data: CustomerLogin) -> dict:
    """客戶登入認證"""
    # 查詢客戶
    customer = db.query(Customer).filter(Customer.email == login_data.email).first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="電子郵件或密碼錯誤"
        )
    
    # 驗證密碼
    if not verify_password(login_data.password, customer.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="電子郵件或密碼錯誤"
        )
    
    # 檢查帳號是否啟用
    if not customer.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="帳號已被停用"
        )
    
    # 生成 Token
    access_token = create_access_token(
        data={"sub": customer.id, "type": "customer"}
    )
    
    logger.info(f"客戶登入成功：{customer.email}")
    
    return {
        "message": "登入成功",
        "customer": {
            "id": customer.id,
            "email": customer.email,
            "name": customer.name
        },
        "access_token": access_token,
        "token_type": "bearer"
    }


def authenticate_admin(db: Session, login_data: AdminLogin) -> dict:
    """管理員登入認證"""
    # 查詢管理員
    admin = db.query(User).filter(User.username == login_data.username).first()
    
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="使用者名稱或密碼錯誤"
        )
    
    # 驗證密碼
    if not verify_password(login_data.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="使用者名稱或密碼錯誤"
        )
    
    # 檢查帳號是否啟用
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="帳號已被停用"
        )
    
    # 生成 Token（包含 type: "admin"）
    access_token = create_access_token(
        data={"sub": admin.id, "type": "admin"}
    )
    
    logger.info(f"管理員登入成功：{admin.username}")
    
    return {
        "message": "登入成功",
        "admin": {
            "id": admin.id,
            "username": admin.username,
            "email": admin.email
        },
        "access_token": access_token,
        "token_type": "bearer"
    }
