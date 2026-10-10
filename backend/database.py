"""
Database abstraction layer for SmartPool.
Module: backend/database.py

Supports:
- Cloud Firestore via Firebase Admin SDK
- Persistent local store fallback when Firestore credentials are not yet supplied
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, List, Optional

try:
    from firebase_config import get_firestore_client, is_firebase_connected
except ImportError:
    from backend.firebase_config import get_firestore_client, is_firebase_connected

logger = logging.getLogger("smartpool.database")

# Persistent file path for fallback local storage
FALLBACK_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_db.json")

_db_lock = RLock()


class DatabaseService:
    def __init__(self):
        self._db_lock = _db_lock
        self._memory_data: Dict[str, Dict[str, Any]] = {
            "users": {},
            "rides": {},
            "drivers": {},
            "dispatches": {},
            "trip_history": {}
        }
        self._load_fallback_db()

    def _load_fallback_db(self):
        """Loads persistent JSON storage if available."""
        if os.path.exists(FALLBACK_DB_PATH):
            try:
                with open(FALLBACK_DB_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for col in ["users", "rides", "drivers", "dispatches", "trip_history"]:
                        self._memory_data[col] = data.get(col, {})
            except Exception as e:
                logger.warning(f"Failed to load fallback db from {FALLBACK_DB_PATH}: {e}")

    def _save_fallback_db(self):
        """Persists memory data to JSON file."""
        try:
            with open(FALLBACK_DB_PATH, "w", encoding="utf-8") as f:
                json.dump(self._memory_data, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Failed to write fallback db: {e}")

    # ==========================================
    # USERS
    # ==========================================

    def save_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        uid = user_data["uid"]
        now_iso = datetime.now(timezone.utc).isoformat()
        user_record = {
            "uid": uid,
            "fullName": user_data.get("fullName", "SmartPool User"),
            "email": user_data.get("email", ""),
            "phone": user_data.get("phone", ""),
            "role": user_data.get("role", "passenger"),
            "provider": user_data.get("provider", "password"),
            "createdAt": user_data.get("createdAt") or now_iso,
            "updatedAt": now_iso
        }

        client = get_firestore_client()
        if client:
            try:
                from firebase_admin import firestore
                doc_ref = client.collection("users").document(uid)
                doc_data = {
                    **user_record,
                    "updatedAt": firestore.SERVER_TIMESTAMP
                }
                if not user_data.get("createdAt"):
                    doc_data["createdAt"] = firestore.SERVER_TIMESTAMP
                doc_ref.set(doc_data, merge=True)
            except Exception as e:
                logger.error(f"Firestore error saving user: {e}")

        with self._db_lock:
            self._memory_data["users"][uid] = user_record
            self._save_fallback_db()

        return user_record

    def get_user(self, uid: str) -> Optional[Dict[str, Any]]:
        client = get_firestore_client()
        if client:
            try:
                doc = client.collection("users").document(uid).get()
                if doc.exists:
                    data = doc.to_dict()
                    # Convert timestamps if necessary
                    return self._serialize_timestamps(data)
            except Exception as e:
                logger.error(f"Firestore error getting user {uid}: {e}")

        with self._db_lock:
            return self._memory_data["users"].get(uid)

    # ==========================================
    # RIDES (BOOKINGS)
    # ==========================================

    def save_ride(self, ride_data: Dict[str, Any]) -> Dict[str, Any]:
        ride_id = ride_data.get("rideId") or ride_data.get("request_id")
        now_iso = datetime.now(timezone.utc).isoformat()

        record = {
            "rideId": ride_id,
            "request_id": ride_id,
            "userId": ride_data.get("userId", "guest"),
            "passengerName": ride_data.get("passengerName") or ride_data.get("passenger_name", "Anonymous"),
            "passenger_name": ride_data.get("passengerName") or ride_data.get("passenger_name", "Anonymous"),
            "passenger_phone": ride_data.get("passenger_phone", ""),
            "pickup": ride_data.get("pickup") or ride_data.get("origin_name", ""),
            "origin_name": ride_data.get("pickup") or ride_data.get("origin_name", ""),
            "destination": ride_data.get("destination") or ride_data.get("destination_name", ""),
            "destination_name": ride_data.get("destination") or ride_data.get("destination_name", ""),
            "origin_engine": ride_data.get("origin_engine", ""),
            "destination_engine": ride_data.get("destination_engine", ""),
            "direct_distance_km": ride_data.get("direct_distance_km", 0.0),
            "seatsRequested": ride_data.get("seatsRequested") or ride_data.get("seats_requested", 1),
            "seats_requested": ride_data.get("seatsRequested") or ride_data.get("seats_requested", 1),
            "maxDetourPercent": ride_data.get("maxDetourPercent") or ride_data.get("max_detour_percent", 15.0),
            "max_detour_percent": ride_data.get("maxDetourPercent") or ride_data.get("max_detour_percent", 15.0),
            "status": ride_data.get("status", "pending"),
            "assignedDriverId": ride_data.get("assignedDriverId", None),
            "dispatchId": ride_data.get("dispatchId", None),
            "is_demo": ride_data.get("is_demo", False),
            "createdAt": ride_data.get("createdAt") or now_iso,
            "updatedAt": now_iso
        }

        client = get_firestore_client()
        if client:
            try:
                from firebase_admin import firestore
                doc_ref = client.collection("rides").document(ride_id)
                firestore_data = {
                    **record,
                    "updatedAt": firestore.SERVER_TIMESTAMP
                }
                if not ride_data.get("createdAt"):
                    firestore_data["createdAt"] = firestore.SERVER_TIMESTAMP
                doc_ref.set(firestore_data, merge=True)
            except Exception as e:
                logger.error(f"Firestore error saving ride {ride_id}: {e}")

        with self._db_lock:
            self._memory_data["rides"][ride_id] = record
            self._save_fallback_db()

        return record

    def get_pending_rides(self) -> List[Dict[str, Any]]:
        """Returns all rides with status == 'pending'."""
        client = get_firestore_client()
        if client:
            try:
                docs = client.collection("rides").where("status", "==", "pending").stream()
                pending = []
                for d in docs:
                    pending.append(self._serialize_timestamps(d.to_dict()))
                # Update memory cache
                with self._db_lock:
                    for r in pending:
                        self._memory_data["rides"][r["rideId"]] = r
                return pending
            except Exception as e:
                logger.error(f"Firestore error querying pending rides: {e}")

        with self._db_lock:
            return [
                r for r in self._memory_data["rides"].values()
                if r.get("status") == "pending"
            ]

    def update_ride_status(
        self,
        ride_id: str,
        status: str,
        assigned_driver_id: Optional[str] = None,
        dispatch_id: Optional[str] = None
    ):
        now_iso = datetime.now(timezone.utc).isoformat()
        client = get_firestore_client()
        if client:
            try:
                from firebase_admin import firestore
                updates = {
                    "status": status,
                    "updatedAt": firestore.SERVER_TIMESTAMP
                }
                if assigned_driver_id is not None:
                    updates["assignedDriverId"] = assigned_driver_id
                if dispatch_id is not None:
                    updates["dispatchId"] = dispatch_id

                client.collection("rides").document(ride_id).update(updates)
            except Exception as e:
                logger.error(f"Firestore error updating ride {ride_id}: {e}")

        with self._db_lock:
            if ride_id in self._memory_data["rides"]:
                self._memory_data["rides"][ride_id]["status"] = status
                if assigned_driver_id is not None:
                    self._memory_data["rides"][ride_id]["assignedDriverId"] = assigned_driver_id
                if dispatch_id is not None:
                    self._memory_data["rides"][ride_id]["dispatchId"] = dispatch_id
                self._memory_data["rides"][ride_id]["updatedAt"] = now_iso
                self._save_fallback_db()

    def get_user_rides(self, user_id: str) -> List[Dict[str, Any]]:
        """Returns all rides requested by a specific user."""
        client = get_firestore_client()
        if client:
            try:
                docs = client.collection("rides").where("userId", "==", user_id).stream()
                user_rides = [self._serialize_timestamps(d.to_dict()) for d in docs]
                user_rides.sort(key=lambda x: str(x.get("createdAt", "")), reverse=True)
                return user_rides
            except Exception as e:
                logger.error(f"Firestore error getting rides for user {user_id}: {e}")

        with self._db_lock:
            user_rides = [
                r for r in self._memory_data["rides"].values()
                if r.get("userId") == user_id
            ]
            user_rides.sort(key=lambda x: str(x.get("createdAt", "")), reverse=True)
            return user_rides

    # ==========================================
    # DRIVERS
    # ==========================================

    def save_driver(self, driver_data: Dict[str, Any]) -> Dict[str, Any]:
        user_id = driver_data["userId"]
        now_iso = datetime.now(timezone.utc).isoformat()
        record = {
            "userId": user_id,
            "fullName": driver_data.get("fullName", "Driver"),
            "phone": driver_data.get("phone", ""),
            "vehicleNumber": driver_data.get("vehicleNumber", "MH-14-SP-2026"),
            "vehicleType": driver_data.get("vehicleType", "Sedan"),
            "totalSeats": driver_data.get("totalSeats", 4),
            "availableSeats": driver_data.get("availableSeats", 4),
            "availabilityStatus": driver_data.get("availabilityStatus", "active"),
            "createdAt": driver_data.get("createdAt") or now_iso,
            "updatedAt": now_iso
        }

        client = get_firestore_client()
        if client:
            try:
                from firebase_admin import firestore
                doc_ref = client.collection("drivers").document(user_id)
                doc_ref.set({
                    **record,
                    "updatedAt": firestore.SERVER_TIMESTAMP
                }, merge=True)
            except Exception as e:
                logger.error(f"Firestore error saving driver {user_id}: {e}")

        with self._db_lock:
            self._memory_data["drivers"][user_id] = record
            self._save_fallback_db()

        return record

    def get_driver(self, user_id: str) -> Optional[Dict[str, Any]]:
        client = get_firestore_client()
        if client:
            try:
                doc = client.collection("drivers").document(user_id).get()
                if doc.exists:
                    return self._serialize_timestamps(doc.to_dict())
            except Exception as e:
                logger.error(f"Firestore error getting driver {user_id}: {e}")

        with self._db_lock:
            return self._memory_data["drivers"].get(user_id)

    # ==========================================
    # DISPATCHES & TRIP HISTORY
    # ==========================================

    def save_dispatch(self, dispatch_data: Dict[str, Any]) -> Dict[str, Any]:
        dispatch_id = dispatch_data.get("dispatchId") or f"disp_{int(time.time())}_{os.urandom(3).hex()}"
        now_iso = datetime.now(timezone.utc).isoformat()

        record = {
            "dispatchId": dispatch_id,
            "matchedRideIds": dispatch_data.get("matchedRideIds", []),
            "driverAssignment": dispatch_data.get("driverAssignment", None),
            "optimizedRoute": dispatch_data.get("optimizedRoute", {}),
            "routeStops": dispatch_data.get("routeStops", []),
            "computedFareBreakdown": dispatch_data.get("computedFareBreakdown", {}),
            "totalDistance": dispatch_data.get("totalDistance", 0.0),
            "detourInformation": dispatch_data.get("detourInformation", {}),
            "dispatchStatus": dispatch_data.get("dispatchStatus", "active"),
            "createdAt": now_iso
        }

        client = get_firestore_client()
        if client:
            try:
                from firebase_admin import firestore
                client.collection("dispatches").document(dispatch_id).set({
                    **record,
                    "createdAt": firestore.SERVER_TIMESTAMP
                })
            except Exception as e:
                logger.error(f"Firestore error saving dispatch: {e}")

        with self._db_lock:
            self._memory_data["dispatches"][dispatch_id] = record
            self._save_fallback_db()

        return record

    def save_trip_history(self, trip_item: Dict[str, Any]) -> Dict[str, Any]:
        trip_id = trip_item.get("tripId") or f"th_{int(time.time())}_{os.urandom(3).hex()}"
        now_iso = datetime.now(timezone.utc).isoformat()

        record = {
            "tripId": trip_id,
            "userId": trip_item.get("userId", "guest"),
            "relatedRideId": trip_item.get("relatedRideId", ""),
            "dispatchId": trip_item.get("dispatchId", ""),
            "pickup": trip_item.get("pickup", ""),
            "destination": trip_item.get("destination", ""),
            "fare": trip_item.get("fare", 0.0),
            "tripStatus": trip_item.get("tripStatus", "completed"),
            "completionTimestamp": now_iso
        }

        client = get_firestore_client()
        if client:
            try:
                from firebase_admin import firestore
                client.collection("trip_history").document(trip_id).set({
                    **record,
                    "completionTimestamp": firestore.SERVER_TIMESTAMP
                })
            except Exception as e:
                logger.error(f"Firestore error saving trip history: {e}")

        with self._db_lock:
            self._memory_data["trip_history"][trip_id] = record
            self._save_fallback_db()

        return record

    def get_user_trip_history(self, user_id: str) -> List[Dict[str, Any]]:
        client = get_firestore_client()
        if client:
            try:
                docs = client.collection("trip_history").where("userId", "==", user_id).stream()
                trips = [self._serialize_timestamps(d.to_dict()) for d in docs]
                trips.sort(key=lambda x: str(x.get("completionTimestamp", "")), reverse=True)
                return trips
            except Exception as e:
                logger.error(f"Firestore error reading trip history for {user_id}: {e}")

        with self._db_lock:
            trips = [
                th for th in self._memory_data["trip_history"].values()
                if th.get("userId") == user_id
            ]
            trips.sort(key=lambda x: str(x.get("completionTimestamp", "")), reverse=True)
            return trips

    def clear_queue_for_demo(self):
        """Clears queue for demo testing while keeping history."""
        with self._db_lock:
            for r in list(self._memory_data["rides"].values()):
                if r.get("status") == "pending":
                    r["status"] = "cancelled"
            self._save_fallback_db()

        client = get_firestore_client()
        if client:
            try:
                docs = client.collection("rides").where("status", "==", "pending").stream()
                for d in docs:
                    d.reference.update({"status": "cancelled"})
            except Exception as e:
                logger.error(f"Firestore error clearing pending queue for demo: {e}")

    def _serialize_timestamps(self, doc_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Converts Firestore DatetimeWithNanoseconds to ISO strings."""
        if not doc_dict:
            return {}
        result = {}
        for k, v in doc_dict.items():
            if hasattr(v, "isoformat"):
                result[k] = v.isoformat()
            elif isinstance(v, dict):
                result[k] = self._serialize_timestamps(v)
            else:
                result[k] = v
        return result


# Global Singleton Database Service Instance
db_service = DatabaseService()
