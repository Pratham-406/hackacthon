# SmartPool — A better way together

Premium React interface for the existing Pune–Mumbai ride-pooling engine.

## Start on Windows

1. Keep your current project folder as a backup. Stop its frontend and backend terminals with Ctrl+C.
2. Extract this ZIP into a NEW folder (for example Documents\SmartPool-Redesign). Do not overlay it onto the old node_modules folder.
3. Install Node.js LTS and Python 3.10 or newer if they are not already installed. Open a new terminal after installation.
4. Double-click START_BACKEND.bat. Leave this window open. Wait for “Application startup complete”.
5. Double-click START_FRONTEND.bat. Leave this window open. Wait for the Vite local URL.
6. Open http://localhost:3000. The header should say “Engine connected”.
7. To return to the old version, stop these two windows and start the scripts in your backup folder.

First launch needs internet to install dependencies. Map tiles need internet whenever used. No map API key is required.

Manual commands, from the extracted project folder, in two terminals:

```bat
py -m pip install -r requirements-demo.txt
py -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

```bat
cd frontend
npm ci
npm run dev
```

If `py` is unavailable but `python --version` works, replace `py` with `python`.
If port 3000 or 8000 is occupied, stop the previous project. The frontend proxy expects port 8000.
Do not open dist/index.html by double-clicking it: the app needs an HTTP server and API proxy.

## Two-minute judge demonstration

1. Select **Dispatch** at the top (bottom navigation on phones).
2. On an empty queue, click **Golden Corridor**, then **Dispatch batch**.
3. Open **Live corridor map**. Recenter, inspect stop markers, and play the clearly labelled simulation.
4. Open **Drive** to see next stops, the pickup/drop-off timeline, and simulated seat occupancy.
5. Return to **Dispatch → Fairness Lab**: Rahul ₹504, Priya ₹728, Aman ₹868; total ₹2,100.
6. Open **Convenience Shield → Test Vikram insertion** to show the fixed 18.1% rejection scenario.
7. Open **What-If Sandbox**, adjust tolerance or add a candidate, and evaluate with the backend.
8. Open **Benchmark scorecard → Load benchmark**. Explain that this existing endpoint supplies a fixed fixture, not a newly measured benchmark.

To demonstrate a passenger: choose **Ride**, enter a name and forward corridor trip, and press **Find a shared ride**. The request is added to the actual server queue. Press **Match current batch** for manual dispatch. A successful response shows that passenger’s fare and route; a single-rider result is explicitly identified. To test shared passenger matching, add another overlapping request from Dispatch before dispatching.

## What changed

- White map-first passenger interface with booking sheet, matching state, trip result, fare explanation and companion list.
- Dark driver console with optimized timeline, next stop, simulation controls and seat occupancy.
- Dark admin sidebar with all six technical sections, real queue controls, fare comparisons and charts.
- Responsive layouts and mobile bottom navigation; keyboard focus, labels and reduced-motion support.
- Leaflet OpenStreetMap tiles, attribution, zoom, fitBounds, location request, safe text popups, pickup/drop-off markers and labelled corridor lines.
- API adapter carries canonical node IDs and uses actual seat counts from dispatch request metadata.
- Production frontend build included in frontend/dist.

## Backend compatibility and honest limits

All uploaded backend Python files and backend/requirements.txt are byte-for-byte unchanged.
The additional root requirements-demo.txt installs WebSocket support for the launcher without editing the backend.

- Existing booking, queue, dispatch, Golden demo, health, node, rejection, benchmark, optimization and WebSocket routes are used.
- The queue is in-memory and dispatch is manual. A server restart clears requests. The heartbeat is not an automatic batching countdown.
- There is no private-booking, cancellation, authentication, payment, live GPS or driver assignment API. The UI does not claim to provide these.
- A successful result is a demo route computation, not an actual transport reservation.
- Routes connect the backend's simplified corridor coordinates. They are not road-following or turn-by-turn navigation. Vehicle movement advances through model stops.
- State for the displayed trip lives in this browser session. Reloading loses the displayed trip. Another browser can update the queue, but this API has no endpoint to retrieve another browser’s dispatched trip.
- Golden Corridor replaces the server queue, so the UI only allows loading it when the queue is empty.
- The rejection endpoint is a fixed Vikram scenario. Its SOLO_DISPATCH field is illustrative and does not create a private ride.
- The benchmark endpoint returns fixed constants. The UI labels them as a fixture, not a new Monte Carlo run.
- Booking and batch dispatch enforce at most 15% detour. The What-If optimization endpoint can evaluate a relaxed cap up to 25%; it is explicitly separate from booking policy.
- What-If calls the existing optimize endpoint, which writes backend/snapshot.json as it already did. It does not replace the displayed trip or alter the booking queue.
- The engine prices each named request, not each seat; the UI preserves these results. Seat counts are used for queue admission and displayed occupancy.
- Backend miles/coordinates are authoritative; fixed screenshot numbers are never used as fallback fares.

## Verify

```bat
cd frontend
npm run build
cd ..
py -m pip install httpx
py -m unittest discover -s tests -v
py tests/export_fixture.py
node tests/check_frontend_adapter.mjs
```

See TEST_RESULTS.md for checks performed and remaining limits. 
🚗 Driver Portal System

A modern, scalable fleet and driver management portal built to streamline trip assignments, booking workflows, and real-time operations.

📌 Project Overview

The Driver Portal provides a seamless interface for dispatchers and drivers to manage, track, and complete trips efficiently. The current release fully implements the end-to-end Booking Process, establishing the core operational foundation for future driver management capabilities.

✅ Completed Features (Current Release)

🎫 Booking Process Engine

Trip Creation & Dispatch: Create and assign trips based on driver availability and route parameters.

Booking Workflow: Complete booking life-cycle management (Pending ➔ Confirmed ➔ Assigned ➔ In Progress ➔ Completed / Cancelled).

Route & Location Integration: Address geocoding and basic route plotting for pickup and drop-off locations.

Fare & Booking Calculation: Automated trip estimate and pricing breakdown during booking creation.

Real-time Status Updates: Instant booking status synchronization between the dispatch server and driver clients.

🚀 Upcoming Features & Roadmap

The following modules are planned for subsequent releases to complete the Driver Portal ecosystem:

Phase 1: Driver Profile & Compliance Management

[ ] Onboarding & Verification: Digital document upload (driver's license, vehicle registration, insurance).

[ ] Compliance Tracking: Automated alerts for document expiration and license renewals.

[ ] Shift & Availability Toggle: Online/offline status management for drivers.

Phase 2: Live Tracking & Navigation

[ ] GPS Real-Time Tracking: Live location streaming via WebSockets/MQTT.

[ ] Turn-by-Turn Navigation: In-app integration with Mapbox / Google Maps SDK.

[ ] Geofencing: Automatic arrival and departure triggers at pickup and drop-off zones.

Phase 3: Electronic Proof of Delivery (PoD)

[ ] Digital Signatures: Capture customer signatures upon trip completion.

[ ] Photo & Inspection Capture: Upload proof-of-delivery photos and vehicle damage logs.

[ ] Barcode / QR Code Scanning: Fast verification of packages and cargo.

Phase 4: Financials & Analytics

[ ] Driver Earnings Dashboard: Daily, weekly, and monthly payout breakdowns.

[ ] Hours of Service (HOS) Logs: Electronic logging logs to monitor driving hours and rest periods.

[ ] Driver Safety & Performance Scorecard: Analytics on punctuality, customer ratings, and driving habits.

🛠️ Technology Stack

Frontend: React / React Native / Vue.js

Backend: Node.js (Express / NestJS) / Python (FastAPI)

Database: PostgreSQL (with PostGIS for spatial data) / MongoDB

Real-Time Data: WebSockets / Redis

Containerization: Docker & Docker Compose

💻 Getting Started

Prerequisites

Docker & Docker Compose

Node.js (v18+)

Running locally with Docker

Clone the repository:

git clone https://github.com/your-username/driver-portal.git
cd driver-portal


Set up Environment Variables:

cp .env.example .env


Start the application and database:

docker-compose up -d --build


Verify services:

Web Portal: http://localhost:3000

API Gateway / Backend: http://localhost:5000
https://github.com/HimanshuAttarde/Driver-Interface-UI
