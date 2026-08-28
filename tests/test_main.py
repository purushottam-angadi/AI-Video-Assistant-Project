def test_signup_sucess(client):
    response=client.post("/signup", json={
        "username":"newuser",
        "password": "Securepass123"
    })
    assert response.status_code ==201
    data=response.json()
    assert data["message"]=="User created successfully"
    assert "user_id" in data

def test_signup_duplicate_username_fails(client, existing_user):

    response= client.post("/signup", json={
        "username": existing_user["username"],
        "password": "AnotherPassword123"
    })

    assert response.status_code== 400
    assert response.json()["detail"]== "Username already exists"


def test_signup_missing_password(client):

    response=client.post("/signup",json={"username": "onlyusername"})
    assert response.status_code ==422



def test_login_success(client, existing_user):
    response=client.post("/login",data={
        "username": existing_user["username"],
        "password": existing_user["password"]
    })
    assert response.status_code ==200
    data= response.json()
    assert "access_token" in data
    assert data["token_type"]=="bearer"



def test_login_wrong_password_fails(client, existing_user):

    response = client.post("/login", data={
        "username": existing_user["username"],
        "password": "WrongPassword!",
    })

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid username or password"


def test_login_wrong_username_fails(client):

    response = client.post("/login", data={
        "username": "ghost_user",
        "password": "WhateverPassword!",
    })

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid username or password"


#/me

def test_me_without_token_fails(client):
    response = client.get("/me")
    assert response.status_code ==401
 
 

def test_me_with_token_fails(client):
    response=client.get("/me", headers={"Authorization": "Bearer this.is.not.a.valid.token"})
    assert response.status_code ==401
    assert response.json()["detail"] == "Could not validate credentials"

def test_me_with_token_success(client, existing_user):
    login_response= client.post("/login", 
                          data={"username": existing_user["username"],
                                 "password": existing_user["password"]})

    token= login_response.json()["access_token"]

    response= client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert "user_id" in response.json()

from unittest.mock import patch




#process part :-

def get_auth_header(client, user_payload):
    response = client.post("/login", data=user_payload)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def fake_run_pipeline(source, language, user_id):
    return {
        "title": "Fake Meeting",
        "transcript": "This is a fake transcript for testing.",
        "summary": "Fake summary.",
        "action_items": "- fake action",
        "key_decisions": "- fake decision",
        "open_questions": "- fake question",
        "retriever": f"fake_retriever_for_{user_id}",
    }

from unittest.mock import patch


def get_auth_header(client, user_payload):
    response = client.post("/login", data=user_payload)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def fake_run_pipeline(source, language, user_id):
    return {
        "title": "Fake Meeting",
        "transcript": "This is a fake transcript for testing.",
        "summary": "Fake summary.",
        "action_items": "- fake action",
        "key_decisions": "- fake decision",
        "open_questions": "- fake question",
        "retriever": f"fake_retriever_for_{user_id}",
    }

def test_process_without_token_fails(client):
    response=client.post("/process", data={"language": "english", "youtube_url": "https://youtube.com/watch?v=fake"})
    assert response.status_code==401

def test_chat_without_token_fails(client):
    response = client.post("/chat", json={"question": "What was discussed?"})
    assert response.status_code == 401

def test_process_without_file_upload(client,existing_user):
    headers= get_auth_header(client, existing_user)

    response = client.post(
        "/process",
        data={"language": "english", "youtube_url": ""},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Provide either a file or a YouTube URL"


def test_chat_with_token_after_process_success(client,existing_user):
    headers = get_auth_header(client, existing_user)

    with patch("api.main.run_pipeline", side_effect=fake_run_pipeline):
        client.post(
            "/process",
            data={"language": "english", "youtube_url":"https://youtube.com/watch?v=fake"},
            headers=headers,
        )

    with patch("api.main.main_graph") as mock_graph:
        mock_graph.invoke.return_value = {"answer": "Fake answer from the graph."}
        response = client.post("/chat", json={"question": "What was discussed?"}, headers=headers)

    assert response.status_code==200
    assert response.json()["answer"]=="Fake answer from the graph."


#per_user_isolation_check:

def test_usera_cant_access_userb_retriever(client, existing_user,second_user):
    headers_a= get_auth_header(client, existing_user)
    headers_b= get_auth_header(client, second_user)

    with patch("api.main.run_pipeline", side_effect= fake_run_pipeline):
      response_a = client.post(
            "/process",
            data={"language": "english", "youtube_url": "https://youtube.com/watch?v=fake"},
            headers=headers_a,
        )
      assert response_a.status_code== 200

      response_b = client.post("/chat", json={"question": "What did they discuss?"}, headers=headers_b)

      assert response_b.status_code == 400
      assert response_b.json()["detail"] == "No processed video found for this user. Call /process first"

