from fastapi import Path, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import get_db
from app.services.store_service import get_store_by_slug
from app.utils.auth_utils import get_current_admin

def get_store(store_slug: str = Path(...), db: Session = Depends(get_db)):
    """從 URL slug 取得 store_id，找不到則回傳 404"""
    store = get_store_by_slug(db, store_slug)
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="找不到此商店"
        )
    return store

def get_current_store_admin(
    store = Depends(get_store),
    admin = Depends(get_current_admin)
):
    """驗證當前登入的管理員是否屬於該商店"""
    if admin.store_id != store.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="無權限存取此商店後台"
        )
    return admin


from app.utils.auth_utils import get_current_user

def get_current_store_customer(
    store = Depends(get_store),
    customer = Depends(get_current_user)
):
    """驗證當前登入的客戶是否屬於該商店"""
    if customer.store_id != store.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="無權限存取此商店資料"
        )
    return customer


