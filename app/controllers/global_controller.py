from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import get_db
from app.services.store_service import register_store
from app.services.auth_service import authenticate_admin
from app.utils.validators import AdminLogin
from pydantic import BaseModel, Field

router = APIRouter()

class MerchantRegister(BaseModel):
    store_name: str
    store_slug: str
    admin_email: str
    admin_password: str = Field(..., min_length=6)

@router.post('/merchant/register', status_code=status.HTTP_201_CREATED)
def register_merchant(data: MerchantRegister, db: Session = Depends(get_db)):
    """全球 API: 註冊新商店"""
    try:
        return register_store(
            db=db,
            store_name=data.store_name,
            store_slug=data.store_slug,
            admin_email=data.admin_email,
            admin_password=data.admin_password
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post('/shop/admin/auth/login')
def admin_unified_login(login_data: AdminLogin, db: Session = Depends(get_db)):
    """全域統一後台登入 API (依 Email 決定商店)"""
    try:
        return authenticate_admin(db, store_id=None, login_data=login_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登入失敗"
        )
