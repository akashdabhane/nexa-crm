import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import bad_request, not_found
from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.models import Profile
from app.schemas.profile import ProfileRead, ProfileUpdateAdmin, ProfileUpdateMe

router = APIRouter(tags=["users"])


@router.get("/me", response_model=ProfileRead)
def read_me(user: Profile = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=ProfileRead)
def update_me(
    payload: ProfileUpdateMe,
    user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.full_name = payload.full_name
    db.commit()
    return user


@router.get("/users", response_model=list[ProfileRead])
def list_users(
    _: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """All users — used for 'assign to' dropdowns and the admin users page."""
    return db.scalars(select(Profile).order_by(Profile.full_name)).all()


@router.patch("/users/{user_id}", response_model=ProfileRead)
def update_user(
    user_id: uuid.UUID,
    payload: ProfileUpdateAdmin,
    admin: Profile = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = db.get(Profile, user_id)
    if target is None:
        raise not_found("User")
    if target.id == admin.id and (payload.role not in (None, admin.role) or payload.is_active is False):
        raise bad_request("You cannot change your own role or deactivate yourself")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(target, field, value)
    db.commit()
    return target
