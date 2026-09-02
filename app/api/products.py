"""Product management endpoints (Phase 7).

- ADMIN / MANUFACTURER can create and manage products
- LMO / RETAILER can view products
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models import Product, User, UserRole

router = APIRouter()


class ProductCreate(BaseModel):
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    subcategory: str | None = None
    brand: str | None = None
    description: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    subcategory: str | None = None
    brand: str | None = None
    description: str | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    category: str
    subcategory: str | None
    brand: str | None
    description: str | None


@router.get(
    "/products",
    response_model=list[ProductOut],
    tags=["products"],
    summary="List products (all roles except CONSUMER)",
)
def list_products(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(
        UserRole.ADMIN, UserRole.LMO, UserRole.MANUFACTURER, UserRole.RETAILER
    )),
) -> list[ProductOut]:
    products = db.query(Product).order_by(Product.created_at.desc()).all()
    return [ProductOut.model_validate(p) for p in products]


@router.get(
    "/products/{product_id}",
    response_model=ProductOut,
    tags=["products"],
    summary="Get a product by id",
)
def get_product(
    product_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(
        UserRole.ADMIN, UserRole.LMO, UserRole.MANUFACTURER, UserRole.RETAILER
    )),
) -> ProductOut:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductOut.model_validate(product)


@router.post(
    "/products",
    response_model=ProductOut,
    status_code=201,
    tags=["products"],
    summary="Create a product (ADMIN / MANUFACTURER)",
)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANUFACTURER)),
) -> ProductOut:
    product = Product(
        name=payload.name,
        category=payload.category,
        subcategory=payload.subcategory,
        brand=payload.brand,
        description=payload.description,
        created_by=user.id,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return ProductOut.model_validate(product)


@router.patch(
    "/products/{product_id}",
    response_model=ProductOut,
    tags=["products"],
    summary="Update a product (ADMIN, or MANUFACTURER who created it)",
)
def update_product(
    product_id: str,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANUFACTURER)),
) -> ProductOut:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if user.role == UserRole.MANUFACTURER and product.created_by != user.id:
        raise HTTPException(status_code=403, detail="Not your product")

    if payload.name is not None:
        product.name = payload.name
    if payload.category is not None:
        product.category = payload.category
    if payload.subcategory is not None:
        product.subcategory = payload.subcategory
    if payload.brand is not None:
        product.brand = payload.brand
    if payload.description is not None:
        product.description = payload.description

    db.commit()
    db.refresh(product)
    return ProductOut.model_validate(product)


@router.delete(
    "/products/{product_id}",
    status_code=204,
    tags=["products"],
    summary="Delete a product (ADMIN, or MANUFACTURER who created it)",
)
def delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANUFACTURER)),
) -> None:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if user.role == UserRole.MANUFACTURER and product.created_by != user.id:
        raise HTTPException(status_code=403, detail="Not your product")
    db.delete(product)
    db.commit()
