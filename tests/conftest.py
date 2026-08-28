import os
import pytest
from fastapi.testclient import TestClient

from dotenv import load_dotenv
load_dotenv()

db_url= os.getenv("DATABASE_URL")


if not db_url:
    raise RuntimeError("Database_URL is not set. Point it at a TEST database before running")


# if "test" not in db_url.lower():
#     raise RuntimeError(
#         f"\n\n🛑 REFUSING TO RUN TESTS.\n"
#         f"DATABASE_URL does not contain 'test': {db_url}\n"
#     )

from api.main import app
from api.auth import get_db, init_db


@pytest.fixture(scope="session",autouse=True)

def setup_test_database():
    init_db()
    yield

def clean_users_table():
    con= get_db()
    cur= con.cursor()
    cur.execute("DELETE FROM users")
    con.commit()
    cur.close()
    con.close()
    yield


@pytest.fixture(autouse=True)
def clean_users_table():
    con = get_db()
    cur = con.cursor()
    cur.execute("TRUNCATE TABLE users RESTART IDENTITY CASCADE;")
    con.commit()
    cur.close()
    con.close()
    yield

    
@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def existing_user(client):
    payload={"username": "existinguser", "password":"Securepass1234"}
    response=client.post("/signup",json=payload)
    assert response.status_code==201, f"Setup failed: {response.text}"
    return payload



@pytest.fixture
def second_user(client):
    payload = {"username": "seconduser", "password": "SecondSecurePass123"}
    response = client.post("/signup", json=payload)
    assert response.status_code == 201, f"Setup failed: {response.text}"
    return payload



@pytest.fixture(autouse=True)
def clean_retriever_store():
    from api.main import RETRIEVER_STORE
    RETRIEVER_STORE.clear()
    yield
    RETRIEVER_STORE.clear()