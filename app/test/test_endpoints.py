import asyncio

import pytest
from dotenv import load_dotenv
from httpx import AsyncClient
from sqlalchemy_utils.functions import drop_database

load_dotenv()

from config import settings

settings.DB_URL = "sqlite+aiosqlite:///adimen_test_db_test"

from db.db import create_db_and_tables
from app.app import app, on_init, on_shutdown


@pytest.fixture(scope="session")
async def asyncio_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield
    loop.close()


@pytest.fixture(scope="session")
async def client(asyncio_loop):
    async with AsyncClient(app=app, base_url="http://localhost") as res:
        await create_db_and_tables()
        await on_init(res)
        yield res
        await on_shutdown(res)
        drop_database(settings.DB_URL)


@pytest.fixture(scope="session")
async def jwt_token(client):
    response = await client.post(
        url="/auth/jwt/login",
        headers={"ContentType": "multipart/form-data"},
        data={"username": "test@api.com", "password": "123"},
    )
    res = response.json()
    return res["access_token"]


@pytest.mark.anyio
async def test_endpoints(client):
    endpoints = (
        ("brand", "POST"),
        ("brand/1", "GET"),
        ("brand/1", "PATCH"),
        ("brand/1", "DELETE"),
        ("vehicle", "POST"),
        ("vehicle/1", "GET"),
        ("vehicle/1", "PATCH"),
        ("vehicle/1", "DELETE"),
    )
    for endpoint in endpoints:
        response = await client.request(
            url=f"/api/{endpoint[0]}", method=endpoint[1], json={}
        )
        assert response.status_code == 401, f"{endpoint[1]} /api/{endpoint[0]}"


async def authorized_request(client, jwt_token, url, method, data=None):
    return await client.request(
        method=method,
        url=url,
        headers={
            "Authorization": f"Bearer {jwt_token}",
            "Content-type": "application/json",
        },
        json=data,
    )


@pytest.mark.anyio
async def test_brand_create(client, jwt_token):
    # new brand should be created
    brand = {"name": "toyota"}
    response = await authorized_request(client, jwt_token, "/api/brand", "POST", brand)
    assert response.status_code == 200

    # duplicate brand name not allowd
    response = await authorized_request(client, jwt_token, "/api/brand", "POST", brand)
    assert response.status_code == 400


@pytest.mark.anyio
async def test_brand_get(client, jwt_token):
    # getting existing brand
    response = await authorized_request(client, jwt_token, "/api/brand/1", "GET")
    assert response.status_code == 200
    assert response.json()["name"] == "toyota"

    # getting non existing brand
    response = await authorized_request(client, jwt_token, "/api/brand/111", "GET")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_brand_update(client, jwt_token):
    # updating existing brand
    brand = {"name": "toyota2"}
    response = await authorized_request(
        client, jwt_token, "/api/brand/1", "PATCH", brand
    )
    assert response.status_code == 200

    response = await authorized_request(client, jwt_token, "/api/brand/1", "GET")
    assert response.status_code == 200
    assert response.json()["name"] == "toyota2"


@pytest.mark.anyio
async def test_vehicle_create(client, jwt_token):
    # new vehicle should be created
    vehicle = {"name": "corolla", "year": 2010, "brand_id": 1}
    response = await authorized_request(
        client, jwt_token, "/api/vehicle", "POST", vehicle
    )
    assert response.status_code == 200, "valid vahicle not created"

    # duplicate vehicle name per brand is not allowed
    response = await authorized_request(
        client, jwt_token, "/api/vehicle", "POST", vehicle
    )
    assert response.status_code == 400, "duplicate vehicle name per brand"

    # invalid request should not pass
    vehicle = {"name": "corolla", "year": 2010}
    response = await authorized_request(
        client, jwt_token, "/api/vehicle", "POST", vehicle
    )
    assert response.status_code == 422, "invalid request unexpected status"

    # vehicle with the same name under different brand is allowed
    brand = {"name": "toyota3"}
    response = await authorized_request(client, jwt_token, "/api/brand", "POST", brand)
    assert response.status_code == 200, "failed create temp brand"
    brand_id = response.json()["id"]
    vehicle = {"name": "corolla", "year": 2010, "brand_id": brand_id}
    response = await authorized_request(
        client, jwt_token, "/api/vehicle", "POST", vehicle
    )
    assert (
        response.status_code == 200
    ), "failed create same vehicle under different brand"
    dupl_vehicle_id = response.json()["id"]

    # duplicate vehicle exists
    response = await authorized_request(
        client, jwt_token, f"/api/vehicle/{dupl_vehicle_id}", "GET"
    )
    assert response.status_code == 200, "duplicate vehicle does not exist"

    response = await authorized_request(
        client, jwt_token, f"/api/brand/{brand_id}", "DELETE"
    )
    assert response.status_code == 200, "failed delete temp brand"

    # duplicate vehicle is deleted with its brand
    response = await authorized_request(
        client, jwt_token, f"/api/vehicle/{dupl_vehicle_id}", "GET"
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_vehicle_get(client, jwt_token):
    response = await authorized_request(client, jwt_token, f"/api/vehicle/1", "GET")
    assert response.status_code == 200, "vehicle does not exist"

    response = await authorized_request(client, jwt_token, f"/api/vehicle/2", "GET")
    assert response.status_code == 404, "non existing vehicle"


@pytest.mark.anyio
async def test_vehicle_update(client, jwt_token):
    # updating existing vehicle
    vehicle = {"name": "corolla2", "year": 2011}
    response = await authorized_request(
        client, jwt_token, "/api/vehicle/1", "PATCH", vehicle
    )
    assert response.status_code == 200

    # updating non existing vehicle
    vehicle = {"name": "corolla2", "year": 2011}
    response = await authorized_request(
        client, jwt_token, "/api/vehicle/2", "PATCH", vehicle
    )
    assert response.status_code == 404

    response = await authorized_request(client, jwt_token, "/api/vehicle/1", "GET")
    assert response.status_code == 200
    assert response.json()["name"] == "corolla2"
    assert response.json()["year"] == 2011


@pytest.mark.anyio
async def test_vehicle_delete(client, jwt_token):
    # deleting existing vehicle
    response = await authorized_request(client, jwt_token, "/api/vehicle/1", "DELETE")
    assert response.status_code == 200

    response = await authorized_request(client, jwt_token, "/api/vehicle/1", "DELETE")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_brand_delete(client, jwt_token):
    # deleting existing brand
    response = await authorized_request(client, jwt_token, "/api/brand/1", "DELETE")
    assert response.status_code == 200

    response = await authorized_request(client, jwt_token, "/api/brand/1", "DELETE")
    assert response.status_code == 404
