from typing import Optional

import pydantic
from config import logger, settings
from db.db import get_async_session
from db.models import Brand, BrandBase, Vehicle, VehicleBase
from exceptions import AlreadyExists, NotFound
from fastapi import Depends
from sqlalchemy import exc
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, relationship, sessionmaker
from sqlmodel import SQLModel, select


class BrandCreate(BrandBase):
    pass


class BrandUpdate(SQLModel):
    name: str


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(SQLModel):
    name: Optional[str]
    year: Optional[int]

    @pydantic.model_validator(mode="before")
    @classmethod
    def at_least_one(cls, values):
        logger.info(values)
        assert ("name" in values and values["name"] is not None) or (
            "year" in values and values["year"] is not None
        ), "year or name should be passed"
        return values


class CRUD:
    def __init__(self, session):
        self.session = session

    async def create_brand(self, brand: BrandCreate) -> Brand:
        db_brand = Brand.model_validate(brand)
        try:
            self.session.add(db_brand)
            await self.session.commit()
            await self.session.refresh(db_brand)
            return db_brand
        except exc.IntegrityError as e:
            if str(e).find("UNIQUE constraint failed") != -1:
                raise AlreadyExists(brand.name)
            raise

    async def get_brand(self, brand_id: int) -> Brand:
        brand = await self.session.get(Brand, brand_id)
        if not brand:
            raise NotFound(f"brand id={brand_id}")
        # logger.info(brand.vehicles)
        return brand

    async def update_brand(self, brand_id, q: BrandUpdate) -> Brand:
        db_brand = await self.get_brand(brand_id)
        brand = q.model_dump(exclude_unset=True)
        db_brand.sqlmodel_update(brand)
        self.session.add(db_brand)
        await self.session.commit()
        await self.session.refresh(db_brand)
        return db_brand

    async def delete_brand(self, brand_id):
        brand = await self.get_brand(brand_id)
        if not brand:
            raise NotFound(f"brand id={brand_id}")
        await self.session.delete(brand)
        await self.session.commit()

    async def create_vehicle(self, vehicle: VehicleCreate) -> Vehicle:
        try:
            # check if brand exists
            brand = await self.get_brand(vehicle.brand_id)
            if not brand:
                raise NotFound(f"brand id={vehicle.brand_id}")

            # check that Vehicle.name is unique for this brand
            stmt = select(Vehicle).where(
                Vehicle.name == vehicle.name, Vehicle.brand_id == vehicle.brand_id
            )
            exists = await self.session.execute(stmt)
            exists = exists.first()
            if exists:
                raise AlreadyExists(f"vehicle exists {exists}")

            db_vehicle = Vehicle.model_validate(vehicle)
            self.session.add(db_vehicle)
            await self.session.commit()
            await self.session.refresh(db_vehicle)
            return db_vehicle
        except exc.IntegrityError as e:
            if str(e).find("UNIQUE constraint failed") != -1:
                raise AlreadyExists(vehicle.name)
            raise

    async def get_vehicle(self, vehicle_id: int) -> Vehicle:
        vehicle = await self.session.get(Vehicle, vehicle_id)
        if not vehicle:
            raise NotFound(f"vehicle id={vehicle_id}")
        # logger.info(vehicle.brand)
        return vehicle

    async def update_vehicle(self, vehicle_id: int, q: VehicleUpdate) -> Vehicle:
        db_vehicle = await self.get_vehicle(vehicle_id)
        if not db_vehicle:
            raise NotFound(f"vehicle id={vehicle_id}")
        vehicle = q.model_dump(exclude_unset=True)
        db_vehicle.sqlmodel_update(vehicle)
        self.session.add(db_vehicle)
        await self.session.commit()
        await self.session.refresh(db_vehicle)
        return db_vehicle

    async def delete_vehicle(self, vehicle_id: int):
        vehicle = await self.get_vehicle(vehicle_id)
        if not vehicle:
            raise NotFound(f"vehicle id={vehicle_id}")
        await self.session.delete(vehicle)
        await self.session.commit()


def get_crud(session: AsyncSession = Depends(get_async_session)) -> CRUD:
    return CRUD(session=session)
