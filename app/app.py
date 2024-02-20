import asyncio
import traceback
from contextlib import asynccontextmanager
from functools import wraps

import aioboto3
from config import logger, settings, setup_logger
from db.crud import (
    CRUD,
    BrandCreate,
    BrandUpdate,
    VehicleCreate,
    VehicleUpdate,
    get_crud,
)
from db.models import Brand, Vehicle

from exceptions import AppBaseException, NotFound
from fastapi import APIRouter, Depends, FastAPI, Response
from schemas import UserRead, UserUpdate
from users import auth_backend, cavu, create_user, fastapi_users

api_router = APIRouter(dependencies=[Depends(cavu())])


def catch_app_exception(endpoint):
    @wraps(endpoint)
    async def wrapper(*args, **kwargs):
        try:
            res = await endpoint(*args, **kwargs)
            return res
        except NotFound as e:
            logger.error(f"Backend exception: {e}")
            if "response" in kwargs:
                kwargs["response"].status_code = 404
            content = {"error": str(e)}
            return content
        except AppBaseException as e:
            logger.error(f"Backend exception: {e}")
            if "response" in kwargs:
                kwargs["response"].status_code = 400
            content = {"error": str(e)}
            return content
        except Exception as e:
            logger.error(traceback.format_exc())
            if "response" in kwargs:
                kwargs["response"].status_code = 500
            content = {"error": str(e)}
            return content

    return wrapper


@api_router.post("/brand")
@catch_app_exception
async def create_brand_endpoint(
    q: BrandCreate, response: Response, response_model=Brand, crud=Depends(get_crud)
):
    brand = await crud.create_brand(q)
    logger.info(f"created brand: {brand}")
    return brand


@api_router.get("/brand/{brand_id}")
@catch_app_exception
async def get_brand_endpoint(
    brand_id: int, response: Response, response_model=Brand, crud=Depends(get_crud)
):
    brand = await crud.get_brand(brand_id)
    logger.info(f"got brand: {brand}")
    return brand


@api_router.patch("/brand/{brand_id}")
@catch_app_exception
async def update_brand_endpoint(
    brand_id: int,
    q: BrandUpdate,
    response: Response,
    response_model=Brand,
    crud=Depends(get_crud),
):
    logger.info(f"updating brand: {brand_id} with {q}")
    brand = await crud.update_brand(brand_id, q)
    logger.info(f"updated brand: {brand_id}")
    return brand


@api_router.delete("/brand/{brand_id}")
@catch_app_exception
async def delete_brand_endpoint(
    brand_id: int, response: Response, crud=Depends(get_crud)
):
    logger.info(f"deleting brand: {brand_id}")
    await crud.delete_brand(brand_id)


@api_router.post("/vehicle")
@catch_app_exception
async def create_vehicle_endpoint(
    q: VehicleCreate,
    response: Response,
    response_model=Vehicle,
    crud: CRUD = Depends(get_crud),
):
    logger.info(f"creating vehicle {q}")
    vehicle = await crud.create_vehicle(q)
    return vehicle


@api_router.get("/vehicle/{vehicle_id}")
@catch_app_exception
async def get_vehicle_endpoint(
    vehicle_id, response: Response, response_model=Vehicle, crud=Depends(get_crud)
):
    logger.info(f"getting vehicle {vehicle_id}")
    vehicle = await crud.get_vehicle(vehicle_id)
    return vehicle


@api_router.patch("/vehicle/{vehicle_id}")
@catch_app_exception
async def update_vehicle_endpoint(
    vehicle_id: int,
    q: VehicleUpdate,
    response: Response,
    response_model=Vehicle,
    crud=Depends(get_crud),
):
    logger.info(f"updating vehicle: {vehicle_id} with {q}")
    vehicle = await crud.update_vehicle(vehicle_id, q)
    logger.info(f"updated vehicle: {vehicle_id}")
    return vehicle


@api_router.delete("/vehicle/{vehicle_id}")
@catch_app_exception
async def delete_vehicle_endpoint(
    vehicle_id: int, response: Response, crud=Depends(get_crud)
):
    logger.info(f"deleting vehicle: {vehicle_id}")
    await crud.delete_vehicle(vehicle_id)


shutdown_event = asyncio.Event()
self_ending_tasks = []


async def sqs_poller():
    session = aioboto3.Session()
    async with session.client("sqs") as sqs:
        while not shutdown_event.is_set():
            res = await sqs.receive_message(
                QueueUrl=str(settings.SQS_QUEUE_URL),
                MaxNumberOfMessages=10,
                WaitTimeSeconds=5,
            )

            if "Messages" in res:
                for msg in res["Messages"]:
                    logger.info(
                        f'Got SQS message: id={msg["MessageId"]} body="{msg["Body"]}"'
                    )

    logger.info("sqs_poller done")


async def on_init(app: FastAPI):
    setup_logger()
    if settings.USER_EMAIL:
        await create_user(settings.USER_EMAIL, settings.USER_PASSWORD, False)
    self_ending_tasks.append(asyncio.create_task(sqs_poller()))


async def on_shutdown(app: FastAPI):
    logger.info("shutdown..")
    shutdown_event.set()
    await asyncio.gather(*self_ending_tasks)
    logger.info("shutdown done")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await on_init(app)

    yield

    await on_shutdown(app)


app = FastAPI(lifespan=lifespan)

app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
# app.include_router(
#     fastapi_users.get_register_router(UserRead, UserCreate),
#     prefix="/auth",
#     tags=["auth"],
# )
# app.include_router(
#     fastapi_users.get_reset_password_router(),
#     prefix="/auth",
#     tags=["auth"],
# )
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

app.include_router(api_router, prefix="/api")
