"""
Unit and integration tests for SmartPool Firebase Authentication,
Firestore Database Layer, and Access Controls.
Run: py -m unittest tests/test_firebase_and_auth.py -v
"""

import unittest
from fastapi.testclient import TestClient
from backend import main
from backend.database import db_service


class FirebaseAuthAndDatabaseTests(unittest.TestCase):
    def setUp(self):
        main.booking_queue.clear()
        self.client = TestClient(main.app)
        self.passenger_token = "test-token-rahul123"
        self.driver_token = "test-token-driver456"
        self.admin_token = "test-token-admin789"

        # Seed profiles
        db_service.save_user({
            "uid": "rahul123",
            "fullName": "Rahul Commuter",
            "email": "rahul@smartpool.local",
            "role": "passenger"
        })
        db_service.save_user({
            "uid": "driver456",
            "fullName": "Dinesh Driver",
            "email": "driver@smartpool.local",
            "role": "driver"
        })
        db_service.save_driver({
            "userId": "driver456",
            "fullName": "Dinesh Driver",
            "vehicleNumber": "MH-14-SP-1001"
        })
        db_service.save_user({
            "uid": "admin789",
            "fullName": "Admin User",
            "email": "admin@smartpool.local",
            "role": "admin"
        })

    def test_health_includes_firestore_flag(self):
        res = self.client.get("/api/system/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("firestore_connected", data)

    def test_unauthenticated_protected_endpoint_rejected(self):
        res = self.client.get("/api/rides/my-history")
        self.assertEqual(res.status_code, 401)
        self.assertIn("detail", res.json())

    def test_authenticated_profile_me(self):
        headers = {"Authorization": f"Bearer {self.passenger_token}"}
        res = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["uid"], "rahul123")
        self.assertEqual(data["role"], "passenger")

    def test_authenticated_profile_update(self):
        headers = {"Authorization": f"Bearer {self.passenger_token}"}
        res = self.client.put("/api/auth/profile", json={"fullName": "Rahul S. Updated", "phone": "+919876543210"}, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["fullName"], "Rahul S. Updated")
        self.assertEqual(data["phone"], "+919876543210")

    def test_authenticated_booking_and_my_history(self):
        headers = {"Authorization": f"Bearer {self.passenger_token}"}
        # Book ride
        book_res = self.client.post("/api/rides/book", json={
            "request_id": "req-rahul-01",
            "passenger_name": "Rahul Commuter",
            "origin_name": "Pune Kiwale Entry",
            "destination_name": "Panvel Highway Exit",
            "seats_requested": 1,
            "max_detour_percent": 15.0
        }, headers=headers)
        self.assertEqual(book_res.status_code, 201)

        # Check history
        hist_res = self.client.get("/api/rides/my-history", headers=headers)
        self.assertEqual(hist_res.status_code, 200)
        hist = hist_res.json()
        self.assertEqual(hist["uid"], "rahul123")
        self.assertTrue(any(r["rideId"] == "req-rahul-01" for r in hist["rides"]))

        # Dispatch batch
        disp_res = self.client.post("/api/rides/batch/dispatch-now", headers=headers)
        self.assertEqual(disp_res.status_code, 200)

        # Verify completed trip is recorded
        hist_after = self.client.get("/api/rides/my-history", headers=headers).json()
        self.assertTrue(any(t["relatedRideId"] == "req-rahul-01" for t in hist_after["trips"]))

    def test_driver_role_authorization(self):
        # Passenger trying to access driver endpoint -> 403 Forbidden
        p_headers = {"Authorization": f"Bearer {self.passenger_token}"}
        res_passenger = self.client.get("/api/driver/assigned-trips", headers=p_headers)
        self.assertEqual(res_passenger.status_code, 403)

        # Driver accessing driver endpoint -> 200 OK
        d_headers = {"Authorization": f"Bearer {self.driver_token}"}
        res_driver = self.client.get("/api/driver/assigned-trips", headers=d_headers)
        self.assertEqual(res_driver.status_code, 200)


if __name__ == "__main__":
    unittest.main()
