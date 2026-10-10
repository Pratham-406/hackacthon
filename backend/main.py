"""
FastAPI Gateway for Pune–Mumbai Expressway Ride-Pooling Engine.

Module: backend/main.py

Endpoints:
- POST /api/optimize-corridor    -> Solves full dispatch and saves state to snapshot.json
- GET  /api/demo/golden-corridor -> 3-commuter scenario (Rahul ₹504, Priya ₹728, Aman ₹868, total ₹2,100, deficit: 0)
- GET  /api/demo/rejection       -> Vikram mid-trip insertion triggering Priya's 18.1% detour violation
- GET  /api/benchmark            -> 100-commuter aggregate benchmark scorecard
- GET  /api/corridor-nodes       -> Registered expressway milestones
- GET  /api/health               -> Gateway health check
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

# Relative / absolute import support
try:
    from engine import (
        CORRIDOR_MILESTONES,
        EXPRESSWAY_NODES,
        RiderRequest as EngineRiderRequest,
        batch_sliding_window_requests,
        run_100_commuter_benchmark,
        simulate_rejection_scenario,
        solve_complete_dispatch,
    )
except ImportError:
    from backend.engine import (
        CORRIDOR_MILESTONES,
        EXPRESSWAY_NODES,
        RiderRequest as EngineRiderRequest,
        batch_sliding_window_requests,
        run_100_commuter_benchmark,
        simulate_rejection_scenario,
        solve_complete_dispatch,
    )

# 1. Initialize FastAPI Application
app = FastAPI(
    title="Pune–Mumbai Expressway Ride-Pooling Engine",
    description="Production Algorithmic Ride-Pooling Gateway for Pune–Mumbai Expressway Corridor",
    version="1.0.0",
)

# 2. CORS Middleware Configuration (allowing all origins and ports, including Vite on 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SNAPSHOT_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshot.json")


# 3. Pydantic Request & Response Schemas
class RiderRequest(BaseModel):
    rider_id: str = Field(..., description="Unique commuter identifier", example="Rahul")
    pickup: str = Field(..., description="Expressway pickup node", example="Pune")
    dropoff: str = Field(..., description="Expressway dropoff node", example="Lonavala")


class BatchDispatchRequest(BaseModel):
    riders: List[RiderRequest] = Field(..., min_items=1, description="List of commuter requests")
    total_fare_inr: Optional[float] = Field(None, description="Optional total vehicle fare in INR (defaults to distance-based)")
    max_detour_pct: Optional[float] = Field(15.0, description="Max allowed detour % (default 15.0%)")
    speed_kmh: Optional[float] = Field(60.0, description="Corridor operating speed in km/h")


class SlidingWindowBatchRequest(BaseModel):
    requests: List[RiderRequest] = Field(..., min_items=1, description="Stream of incoming commuter requests")
    window_minutes: Optional[float] = Field(15.0, description="Sliding temporal batching window in minutes")
    max_cab_capacity: Optional[int] = Field(3, description="Maximum seating capacity per cab")
    max_detour_pct: Optional[float] = Field(15.0, description="Max allowed detour % (default 15.0%)")
    speed_kmh: Optional[float] = Field(60.0, description="Corridor operating speed in km/h")


# 4. API Endpoints

@app.get("/api/health", tags=["System"])
def get_health() -> Dict[str, str]:
    """Gateway health check."""
    return {
        "status": "HEALTHY",
        "service": "Pune–Mumbai Expressway Ride-Pooling Gateway",
        "version": "1.0.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }


@app.get("/api/corridor-nodes", tags=["Topology"])
def get_corridor_nodes() -> Dict[str, Any]:
    """Returns expressway corridor nodes with distance offsets from Pune (0 km)."""
    return {
        "corridor": "Pune–Mumbai Expressway",
        "milestones": CORRIDOR_MILESTONES,
        "nodes": EXPRESSWAY_NODES
    }


@app.post("/api/optimize-corridor", tags=["Dispatch"])
def optimize_corridor(request: BatchDispatchRequest) -> Dict[str, Any]:
    """
    Main dispatch endpoint for frontend and dispatch operations.
    Coordinates VRPTW route sequencing, <=15% detour compliance,
    integer-paise Shapley fair pricing, and persists state to snapshot.json.
    """
    try:
        # Convert Pydantic models to engine domain requests
        engine_riders = [
            EngineRiderRequest(
                rider_id=r.rider_id,
                pickup=r.pickup,
                dropoff=r.dropoff
            )
            for r in request.riders
        ]

        dispatch_result = solve_complete_dispatch(
            riders_list=engine_riders,
            total_fare_inr=request.total_fare_inr,
            max_detour_pct=request.max_detour_pct or 15.0,
            speed_kmh=request.speed_kmh or 60.0
        )

        # Save trip state to snapshot.json
        try:
            with open(SNAPSHOT_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(dispatch_result, f, indent=2)
        except Exception as write_err:
            # Non-blocking log
            print(f"[Warning] Failed to write snapshot.json: {write_err}")

        return dispatch_result

    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Engine optimization failed: {str(e)}"
        )


@app.get("/api/demo/golden-corridor", tags=["Demonstration"])
def get_golden_corridor_demo() -> Dict[str, Any]:
    """
    Returns the 3-commuter scenario:
    - Rahul: ₹504.00 (Pune -> Lonavala)
    - Priya: ₹728.00 (Talegaon -> Panvel)
    - Aman:  ₹868.00 (Lonavala -> Mumbai)
    - Total: ₹2,100.00 | Platform deficit: 0 paise.
    Executes in strictly < 50ms.
    """
    t_start = time.perf_counter()

    golden_riders = [
        EngineRiderRequest("Rahul", "Pune", "Lonavala"),
        EngineRiderRequest("Priya", "Talegaon", "Panvel"),
        EngineRiderRequest("Aman", "Lonavala", "Mumbai"),
    ]

    dispatch_result = solve_complete_dispatch(
        riders_list=golden_riders,
        total_fare_inr=2100.0,
        max_detour_pct=15.0,
        speed_kmh=60.0
    )

    t_latency_ms = (time.perf_counter() - t_start) * 1000.0
    dispatch_result["latency_ms"] = round(t_latency_ms, 3)

    return dispatch_result


@app.get("/api/demo/rejection", tags=["Demonstration"])
def get_demo_rejection() -> Dict[str, Any]:
    """
    Returns Vikram's 18.1% detour rejection scenario.
    Demonstrates hard <=15.0% detour boundary enforcement mid-trip.
    """
    return simulate_rejection_scenario(detour_cap_pct=15.0)


@app.get("/api/benchmark", tags=["Benchmark"])
def get_benchmark() -> Dict[str, Any]:
    """
    Returns the 100-commuter aggregate benchmark scorecard:
    - 34.5% distance reduction
    - 9.8% P95 detour
    - 501.4 kg CO2 reduction
    - +63% driver revenue boost
    - 0 platform deficit
    """
    return run_100_commuter_benchmark()


@app.post("/api/batch/sliding-window", tags=["Batching"])
def run_sliding_window_batch(payload: SlidingWindowBatchRequest) -> Dict[str, Any]:
    """
    Dynamic Sliding-Window Batching Endpoint.
    Asynchronously batches commuter requests arriving over sliding time windows,
    evaluates VRPTW precedence and detour compliance, and generates live route graphs
    with Shapley fair pricing per batch.
    """
    try:
        engine_riders = [
            EngineRiderRequest(rider_id=r.rider_id, pickup=r.pickup, dropoff=r.dropoff)
            for r in payload.requests
        ]
        return batch_sliding_window_requests(
            requests=engine_riders,
            window_minutes=payload.window_minutes or 15.0,
            max_cab_capacity=payload.max_cab_capacity or 3,
            max_detour_pct=payload.max_detour_pct or 15.0,
            speed_kmh=payload.speed_kmh or 60.0
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sliding-window batching failed: {str(e)}"
        )


# Run directly via `python backend/main.py`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

# ---------------------------------------------------------------------------
# SmartPool Production Gateway Integration Endpoints
# Backed by Google Cloud Firestore and Firebase Authentication.
# Preserves 100% backward compatibility with optimization engine & UI adapter.
# ---------------------------------------------------------------------------
from fastapi import Depends, Security, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import field_validator
from threading import RLock
from datetime import datetime, timezone
import asyncio
import uuid

try:
    from .engine import get_direct_distance, get_node_km, normalize_node
except ImportError:
    from engine import get_direct_distance, get_node_km, normalize_node

try:
    from .firebase_config import initialize_firebase_admin, is_firebase_connected
    from .database import db_service
    from .auth import get_current_user, get_optional_user, require_role
except ImportError:
    from firebase_config import initialize_firebase_admin, is_firebase_connected
    from database import db_service
    from auth import get_current_user, get_optional_user, require_role

# Initialize Firebase Admin upon gateway startup
initialize_firebase_admin()

# Frontend displays longer labels; backend engine works with canonical mileposts.
UI_TO_ENGINE_NODE = {
    "Pune Kiwale Entry": "Pune",
    "Talegaon Toll Plaza": "Talegaon",
    "Urse Toll Plaza": "Talegaon",  # Approximate: Urse is not separately modelled by the engine.
    "Lonavala Interchange": "Lonavala",
    "Khandala Ghat": "Khandala",
    "Khalapur Toll Plaza": "Khalapur",
    "Shedung Interchange": "Panvel",  # Approximate: Shedung isn't separately modelled.
    "Panvel Highway Exit": "Panvel",
    "Vashi (Navi Mumbai)": "Vashi",
    "Mumbai Dadar TT Circle": "Mumbai",
}

# Reverse lookup with preferred UI names. Engine also exposes a larger list of aliases.
ENGINE_TO_UI_NODE = {
    "Pune": "Pune Kiwale Entry",
    "Talegaon": "Talegaon Toll Plaza",
    "Lonavala": "Lonavala Interchange",
    "Khandala": "Khandala Ghat",
    "Khalapur": "Khalapur Toll Plaza",
    "Panvel": "Panvel Highway Exit",
    "Vashi": "Vashi (Navi Mumbai)",
    "Mumbai": "Mumbai Dadar TT Circle",
}

class BookingRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    passenger_name: str = Field(min_length=1, max_length=70)
    passenger_phone: str = ""
    origin_name: str
    destination_name: str
    seats_requested: int = Field(default=1, ge=1, le=4)
    max_detour_percent: float = Field(default=15.0, ge=0.0, le=15.0)

class ProfileUpdateRequest(BaseModel):
    fullName: Optional[str] = None
    phone: Optional[str] = None

queue_lock = RLock()
booking_queue: List[Dict[str, Any]] = []
last_dispatched: Optional[Dict[str, Any]] = None

DEMO_RIDERS = [
    {"request_id": "demo-rahul", "passenger_name": "Rahul", "origin_name": "Pune Kiwale Entry", "destination_name": "Lonavala Interchange", "seats_requested": 1, "max_detour_percent": 15.0},
    {"request_id": "demo-priya", "passenger_name": "Priya", "origin_name": "Talegaon Toll Plaza", "destination_name": "Panvel Highway Exit", "seats_requested": 1, "max_detour_percent": 15.0},
    {"request_id": "demo-aman", "passenger_name": "Aman", "origin_name": "Lonavala Interchange", "destination_name": "Mumbai Dadar TT Circle", "seats_requested": 1, "max_detour_percent": 15.0},
]


def _canonical(name: str) -> str:
    return normalize_node(UI_TO_ENGINE_NODE.get(name, name))


def _sync_queue_from_db():
    """Populates in-memory queue from persistent database if needed."""
    global booking_queue
    pending = db_service.get_pending_rides()
    if pending:
        # Preserve items not already in queue
        existing_ids = {r.get('request_id') or r.get('rideId') for r in booking_queue}
        for p in pending:
            p_id = p.get('request_id') or p.get('rideId')
            if p_id not in existing_ids:
                booking_queue.append(p)

# Sync once on initial load
_sync_queue_from_db()

def _queue_response() -> Dict[str, Any]:
    with queue_lock:
        return {"queue_size": len(booking_queue), "requests": [dict(r) for r in booking_queue], "batch_id": "DEMO_WINDOW"}


@app.get('/api/system/health', tags=['Frontend'])
def frontend_health() -> Dict[str, Any]:
    health_data = get_health()
    health_data["firestore_connected"] = is_firebase_connected()
    return health_data


@app.get('/api/rides/queue', tags=['Frontend'])
def get_queue() -> Dict[str, Any]:
    return _queue_response()


@app.post('/api/rides/book', status_code=201, tags=['Frontend'])
def book_ride(
    request: BookingRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
) -> Dict[str, Any]:
    try:
        origin = _canonical(request.origin_name)
        destination = _canonical(request.destination_name)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    if get_node_km(destination) <= get_node_km(origin):
        raise HTTPException(status_code=400, detail='This demo only supports Pune → Mumbai trips; drop-off must be after pickup.')
    if origin == destination:
        raise HTTPException(status_code=400, detail='Pickup and destination cannot be the same node.')
    direct_km = get_direct_distance(origin, destination)
    
    rider = request.model_dump()
    rider['origin_engine'] = origin
    rider['destination_engine'] = destination
    rider['direct_distance_km'] = direct_km

    # Attach authenticated user identity if logged in
    if current_user:
        rider['userId'] = current_user['uid']
        # If user has profile name, preserve requested name or update
        if not rider.get('passenger_name') or rider['passenger_name'] == 'Anonymous':
            rider['passenger_name'] = current_user.get('name', 'Passenger')
    else:
        rider['userId'] = 'guest'

    with queue_lock:
        if any(r['request_id'] == request.request_id for r in booking_queue):
            raise HTTPException(status_code=409, detail='This request is already queued.')
        if any(r['passenger_name'] == request.passenger_name for r in booking_queue):
            raise HTTPException(status_code=409, detail='Use a different passenger name for this demo batch.')

        # Persist to database (Firestore / persistent local db)
        saved_record = db_service.save_ride(rider)
        booking_queue.append(saved_record)
        position = len(booking_queue)

    return {
        'status': 'QUEUED',
        'batch_id': 'DEMO_WINDOW',
        'batch_position': position,
        'corridor_validation': {
            'direct_distance_km': direct_km,
            'origin': origin,
            'destination': destination
        }
    }


@app.post('/api/rides/batch/dispatch-now', tags=['Frontend'])
def dispatch_queued_rides(
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
) -> Dict[str, Any]:
    global last_dispatched
    with queue_lock:
        if not booking_queue:
            _sync_queue_from_db()
        if not booking_queue:
            raise HTTPException(status_code=409, detail='No rides in the queue. Add passengers or load the Golden Corridor first.')

        # One vehicle, at most 4 seats. Preserve unassigned requests for next dispatch.
        selected = []
        for r in booking_queue:
            seats = r.get('seats_requested') or r.get('seatsRequested') or 1
            if sum((x.get('seats_requested') or x.get('seatsRequested') or 1) for x in selected) + seats <= 4:
                selected.append(r)
        if not selected:
            raise HTTPException(status_code=409, detail='No valid capacity match is available.')

        # Overlap validation: shared corridor rides must share at least some road distance
        if len(selected) > 1:
            has_overlap = any(
                min(get_node_km(a['destination_engine']), get_node_km(b['destination_engine'])) >
                max(get_node_km(a['origin_engine']), get_node_km(b['origin_engine']))
                for i, a in enumerate(selected) for b in selected[i + 1:]
            )
            if not has_overlap:
                raise HTTPException(status_code=409, detail='No overlapping route found. Wait for new passengers or dispatch as private rides.')

        riders = [
            EngineRiderRequest(
                x.get('passenger_name') or x.get('passengerName'),
                x['origin_engine'],
                x['destination_engine']
            )
            for x in selected
        ]

        try:
            cap = min(15.0, *(float(x.get('max_detour_percent') or x.get('maxDetourPercent') or 15.0) for x in selected))
            result = solve_complete_dispatch(riders, max_detour_pct=cap)
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))

        if not result.get('is_feasible'):
            raise HTTPException(status_code=409, detail='This combination breaks a passenger detour limit. Try another batch.')

        # 1. Persist the dispatch record to Firestore
        dispatch_doc = db_service.save_dispatch({
            "matchedRideIds": [r.get('request_id') or r.get('rideId') for r in selected],
            "driverAssignment": current_user['uid'] if (current_user and current_user.get('role') == 'driver') else None,
            "optimizedRoute": result.get('route_summary', {}),
            "routeStops": result.get('route_summary', {}).get('stops', []),
            "computedFareBreakdown": result.get('pricing', {}),
            "totalDistance": result.get('route_summary', {}).get('pooled_distance_km', 0.0),
            "detourInformation": result.get('detour_compliance', {}),
            "dispatchStatus": "dispatched"
        })
        dispatch_id = dispatch_doc["dispatchId"]

        # 2. Update matched rides to dispatched & record passenger trip history
        splits = result.get('pricing', {}).get('comparative_splits', {}).get('shapley_fares_inr', {})
        for r in selected:
            r_id = r.get('request_id') or r.get('rideId')
            p_name = r.get('passenger_name') or r.get('passengerName')
            user_id = r.get('userId', 'guest')

            db_service.update_ride_status(
                ride_id=r_id,
                status="dispatched",
                dispatch_id=dispatch_id,
                assigned_driver_id=dispatch_doc.get("driverAssignment")
            )

            fare_amount = splits.get(p_name, 0.0)
            db_service.save_trip_history({
                "userId": user_id,
                "relatedRideId": r_id,
                "dispatchId": dispatch_id,
                "pickup": r.get('origin_name') or r.get('pickup', ''),
                "destination": r.get('destination_name') or r.get('destination', ''),
                "fare": fare_amount,
                "tripStatus": "completed"
            })

        # 3. Remove only matched rides once valid route is confirmed
        selected_ids = {r.get('request_id') or r.get('rideId') for r in selected}
        booking_queue[:] = [r for r in booking_queue if (r.get('request_id') or r.get('rideId')) not in selected_ids]
        last_dispatched = result

    return {
        'status': 'DISPATCHED',
        'matched_requests': len(selected),
        'vkt_savings_km': result['route_summary']['distance_saved_km'],
        'dispatch': result,
        'requests': selected,
        'remaining_queue': _queue_response()['requests']
    }


@app.post('/api/demo/load-golden-queue', tags=['Frontend'])
def load_golden_queue() -> Dict[str, Any]:
    global last_dispatched
    with queue_lock:
        golden_items = [
            dict(
                r,
                origin_engine=_canonical(r['origin_name']),
                destination_engine=_canonical(r['destination_name']),
                direct_distance_km=get_direct_distance(_canonical(r['origin_name']), _canonical(r['destination_name'])),
                userId="demo-rahul" if "rahul" in r['request_id'] else "demo-user",
                is_demo=True,
                status="pending"
            )
            for r in DEMO_RIDERS
        ]
        booking_queue[:] = golden_items
        for item in golden_items:
            db_service.save_ride(item)
        last_dispatched = None
    return _queue_response()


# ---------------------------------------------------------------------------
# Authenticated User & History Endpoints
# ---------------------------------------------------------------------------

@app.get('/api/rides/my-history', tags=['Passenger'])
def get_my_history(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Returns persistent ride bookings and historical completed trips for the authenticated passenger."""
    uid = current_user['uid']
    user_rides = db_service.get_user_rides(uid)
    user_trips = db_service.get_user_trip_history(uid)
    return {
        "uid": uid,
        "rides": user_rides,
        "trips": user_trips,
        "total_rides": len(user_rides),
        "total_trips": len(user_trips)
    }


@app.get('/api/auth/me', tags=['Authentication'])
def get_auth_me(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Returns verified profile and authorization role for the authenticated user."""
    profile = db_service.get_user(current_user['uid'])
    if not profile:
        profile = {
            "uid": current_user['uid'],
            "email": current_user.get('email', ''),
            "fullName": current_user.get('name', 'SmartPool User'),
            "role": current_user.get('role', 'passenger')
        }
    return profile


@app.put('/api/auth/profile', tags=['Authentication'])
def update_profile(
    body: ProfileUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Updates user profile information."""
    uid = current_user['uid']
    existing = db_service.get_user(uid) or {
        "uid": uid,
        "email": current_user.get('email', ''),
        "role": current_user.get('role', 'passenger')
    }
    if body.fullName:
        existing["fullName"] = body.fullName
    if body.phone is not None:
        existing["phone"] = body.phone
    updated = db_service.save_user(existing)
    return updated


@app.get('/api/driver/assigned-trips', tags=['Driver'])
def get_driver_trips(
    current_user: Dict[str, Any] = Depends(require_role(["driver", "admin"]))
) -> Dict[str, Any]:
    """Returns assigned driver route and active dispatch."""
    driver_info = db_service.get_driver(current_user['uid'])
    return {
        "driver": driver_info,
        "active_trip": last_dispatched,
    }


@app.websocket('/ws/corridor')
async def ws_corridor(socket: WebSocket):
    await socket.accept()
    try:
        while True:
            with queue_lock:
                count = len(booking_queue)
            await socket.send_json({'event': 'BATCH_TICK', 'data': {'window_seconds_remaining': 0.0, 'queue_size': count}})
            try:
                await asyncio.wait_for(socket.receive_text(), timeout=2)
            except asyncio.TimeoutError:
                pass
    except (WebSocketDisconnect, RuntimeError):
        return
