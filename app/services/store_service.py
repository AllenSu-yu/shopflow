from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models import Store, User, StoreInfo
from app.utils.auth_utils import hash_password

def register_store(db: Session, store_name: str, store_slug: str, admin_email: str, admin_password: str) -> Store:
    """
    註冊新商店：
    1. 建立 Store
    2. 建立專屬 Admin User（只有 email + 密碼）
    3. 建立 StoreInfo
    """
    # 檢查商店名稱是否已被使用
    existing_name = db.query(Store).filter(Store.name == store_name).first()
    if existing_name:
        raise HTTPException(status_code=400, detail="商店名稱已被註冊過")

    # 檢查網址代碼是否已被使用
    existing_store = db.query(Store).filter(Store.slug == store_slug).first()
    if existing_store:
        raise HTTPException(status_code=400, detail="商店專屬網址已被註冊過")

    # 檢查 email 是否已被使用（全域唯一）
    existing_user = db.query(User).filter(User.email == admin_email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email已被註冊過")

    try:
        # 1. 建立商店
        new_store = Store(
            name=store_name,
            slug=store_slug,
            is_active=True
        )
        db.add(new_store)
        db.flush()  # 取得 new_store.id

        # 2. 建立管理員（只用 email）
        new_admin = User(
            store_id=new_store.id,
            email=admin_email,
            password_hash=hash_password(admin_password)
        )
        db.add(new_admin)

        # 3. 建立基本商店設定檔
        new_store_info = StoreInfo(
            store_id=new_store.id,
            store_name=store_name,
            store_description=f"歡迎來到 {store_name}",
            contact_email=admin_email
        )
        db.add(new_store_info)

        db.commit()
        db.refresh(new_store)
        return new_store

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email已被註冊過")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

def get_store_by_slug(db: Session, slug: str) -> Store:
    store = db.query(Store).options(joinedload(Store.store_info)).filter(Store.slug == slug).first()
    if not store:
        raise HTTPException(status_code=404, detail="找不到此商店")
    return store
