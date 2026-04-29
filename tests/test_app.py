"""
Tests for the Mergington High School Activities API (src/app.py)

These tests verify all API endpoints:
- GET / (redirect to static)
- GET /activities (fetch all activities)
- POST /activities/{activity_name}/signup (register a student)
- DELETE /activities/{activity_name}/signup (unregister a student)
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities(monkeypatch):
    """Reset activities to a known state before each test"""
    test_activities = {
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu"]
        },
        "Basketball Team": {
            "description": "Practice and compete in basketball games",
            "schedule": "Tuesdays and Thursdays, 4:00 PM - 6:00 PM",
            "max_participants": 15,
            "participants": []
        }
    }
    # Monkeypatch the activities dictionary in the app module
    import src.app
    monkeypatch.setattr(src.app, "activities", test_activities)
    return test_activities


# ============================================================================
# GET / (Root endpoint - redirect)
# ============================================================================

def test_get_root(client):
    """Test that GET / redirects to /static/index.html"""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


# ============================================================================
# GET /activities (Fetch all activities)
# ============================================================================

def test_get_activities(client, reset_activities):
    """Test that GET /activities returns all activities"""
    response = client.get("/activities")
    assert response.status_code == 200
    
    data = response.json()
    
    # Verify all activities are returned
    assert "Chess Club" in data
    assert "Programming Class" in data
    assert "Basketball Team" in data
    
    # Verify activity structure
    chess = data["Chess Club"]
    assert chess["description"] == "Learn strategies and compete in chess tournaments"
    assert chess["schedule"] == "Fridays, 3:30 PM - 5:00 PM"
    assert chess["max_participants"] == 12
    assert len(chess["participants"]) == 2
    assert "michael@mergington.edu" in chess["participants"]


def test_get_activities_empty_participants(client, reset_activities):
    """Test that activities with no participants are returned correctly"""
    response = client.get("/activities")
    assert response.status_code == 200
    
    data = response.json()
    basketball = data["Basketball Team"]
    
    assert basketball["participants"] == []
    assert basketball["max_participants"] == 15


# ============================================================================
# POST /activities/{activity_name}/signup (Register for an activity)
# ============================================================================

def test_signup_success(client, reset_activities):
    """Test successfully signing up for an activity"""
    response = client.post(
        "/activities/Basketball Team/signup?email=john@mergington.edu"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Signed up john@mergington.edu for Basketball Team"
    
    # Verify participant was added
    response = client.get("/activities")
    activities = response.json()
    assert "john@mergington.edu" in activities["Basketball Team"]["participants"]


def test_signup_duplicate_email(client, reset_activities):
    """Test that duplicate signup is rejected with 400 error"""
    # michael@mergington.edu is already signed up for Chess Club
    response = client.post(
        "/activities/Chess Club/signup?email=michael@mergington.edu"
    )
    
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Student already signed up for this activity"
    
    # Verify participant list unchanged
    response = client.get("/activities")
    activities = response.json()
    assert len(activities["Chess Club"]["participants"]) == 2


def test_signup_invalid_activity(client, reset_activities):
    """Test that signup for non-existent activity returns 404"""
    response = client.post(
        "/activities/Nonexistent Club/signup?email=student@mergington.edu"
    )
    
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Activity not found"


def test_signup_new_participant(client, reset_activities):
    """Test that a new participant can sign up for an activity with existing participants"""
    response = client.post(
        "/activities/Programming Class/signup?email=alice@mergington.edu"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "alice@mergington.edu" in data["message"]
    
    # Verify participant count increased
    response = client.get("/activities")
    activities = response.json()
    assert len(activities["Programming Class"]["participants"]) == 2
    assert "alice@mergington.edu" in activities["Programming Class"]["participants"]


# ============================================================================
# DELETE /activities/{activity_name}/signup (Unregister from an activity)
# ============================================================================

def test_delete_participant_success(client, reset_activities):
    """Test successfully removing a participant from an activity"""
    response = client.delete(
        "/activities/Chess Club/signup?email=michael@mergington.edu"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Unregistered michael@mergington.edu from Chess Club"
    
    # Verify participant was removed
    response = client.get("/activities")
    activities = response.json()
    assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]
    assert len(activities["Chess Club"]["participants"]) == 1


def test_delete_participant_not_found(client, reset_activities):
    """Test that deleting non-existent participant returns 404"""
    response = client.delete(
        "/activities/Basketball Team/signup?email=nobody@mergington.edu"
    )
    
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Participant not found"


def test_delete_invalid_activity(client, reset_activities):
    """Test that deleting from non-existent activity returns 404"""
    response = client.delete(
        "/activities/Nonexistent Club/signup?email=john@mergington.edu"
    )
    
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Activity not found"


def test_delete_removes_only_target_participant(client, reset_activities):
    """Test that deleting one participant doesn't affect others"""
    # Chess Club has 2 participants
    response = client.delete(
        "/activities/Chess Club/signup?email=daniel@mergington.edu"
    )
    
    assert response.status_code == 200
    
    # Verify only daniel was removed, michael remains
    response = client.get("/activities")
    activities = response.json()
    assert "michael@mergington.edu" in activities["Chess Club"]["participants"]
    assert "daniel@mergington.edu" not in activities["Chess Club"]["participants"]
    assert len(activities["Chess Club"]["participants"]) == 1


# ============================================================================
# Integration tests (signup followed by delete, etc.)
# ============================================================================

def test_signup_then_delete_flow(client, reset_activities):
    """Test the full flow: signup, verify, then delete"""
    # Sign up
    signup_response = client.post(
        "/activities/Basketball Team/signup?email=test@mergington.edu"
    )
    assert signup_response.status_code == 200
    
    # Verify sign-up
    get_response = client.get("/activities")
    activities = get_response.json()
    assert "test@mergington.edu" in activities["Basketball Team"]["participants"]
    
    # Delete
    delete_response = client.delete(
        "/activities/Basketball Team/signup?email=test@mergington.edu"
    )
    assert delete_response.status_code == 200
    
    # Verify deletion
    get_response = client.get("/activities")
    activities = get_response.json()
    assert "test@mergington.edu" not in activities["Basketball Team"]["participants"]


def test_multiple_participants_concurrent_flow(client, reset_activities):
    """Test that multiple participants can sign up and be managed independently"""
    # Sign up multiple participants
    for i in range(3):
        email = f"student{i}@mergington.edu"
        response = client.post(
            f"/activities/Basketball Team/signup?email={email}"
        )
        assert response.status_code == 200
    
    # Verify all 3 signed up
    response = client.get("/activities")
    basketball = response.json()["Basketball Team"]
    assert len(basketball["participants"]) == 3
    
    # Delete one
    response = client.delete(
        "/activities/Basketball Team/signup?email=student1@mergington.edu"
    )
    assert response.status_code == 200
    
    # Verify correct one was deleted
    response = client.get("/activities")
    basketball = response.json()["Basketball Team"]
    assert len(basketball["participants"]) == 2
    assert "student1@mergington.edu" not in basketball["participants"]
    assert "student0@mergington.edu" in basketball["participants"]
    assert "student2@mergington.edu" in basketball["participants"]
