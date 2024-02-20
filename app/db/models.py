from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class BrandBase(SQLModel):
    name: str = Field(nullable=False, index=True, unique=True)


class Brand(BrandBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)

    vehicles: List["Vehicle"] = Relationship(
        back_populates="brand", sa_relationship_kwargs={"cascade": "delete"}
    )


class VehicleBase(SQLModel):
    name: str = Field(nullable=False, index=True)
    year: int = Field(nullable=False)
    brand_id: int = Field(nullable=False, foreign_key="brand.id")


class Vehicle(VehicleBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)

    brand: Brand = Relationship(back_populates="vehicles")
