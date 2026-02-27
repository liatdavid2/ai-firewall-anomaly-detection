# AI Firewall Prototype (Policy + Anomaly Detection)

This project implements a scalable AI-driven firewall backend with policy enforcement, anomaly detection, caching, and rate-limited AI scoring.

---

# Architecture Overview

```
                          ┌────────────────────────────┐
                          │           Clients          │
                          └─────────────┬──────────────┘
                                        │
                                        ▼
                          ┌────────────────────────────┐
                          │           FastAPI          │
                          │                            │
                          │  POST /connections         │
                          │  GET  /connections/{id}    │
                          │  POST /policies            │
                          │  PUT  /policies/{id}       │
                          └─────────────┬──────────────┘
                                        │
          ┌─────────────────────────────┼─────────────────────────────┐
          │                             │                             │
          ▼                             ▼                             ▼

┌──────────────────────┐   ┌──────────────────────┐    ┌──────────────────────┐
│   Connection Flow    │   │    Policy Manager    │    │   Connection Read    │
│                      │   │                      │    │                      │
│ handles:             │   │ handles:             │    │ handles:             │
│ POST /connections    │   │ POST /policies       │    │ GET /connections/{id}│
│                      │   │ PUT  /policies/{id}  │    │                      │
└──────────┬───────────┘   └──────────┬───────────┘    └──────────┬───────────┘
           │                          │                           │
           ▼                          ▼                           ▼

┌──────────────────────┐   ┌──────────────────────┐    ┌──────────────────────┐
│ Connection Storage   │   │   Policy Storage     │    │ Connection Storage   │
│                      │   │                      │    │ (read only)          │
└──────────┬───────────┘   └──────────────────────┘    └──────────────────────┘
           │
           ▼
┌──────────────────────┐
│    Policy Engine     │
└──────────┬───────────┘
   allow/block │ alert / no match
               │
               ▼
      ┌─────────────────────────────┐
      │         AI Gateway          │
      │     submit_for_scoring()    │
      └──────────────┬──────────────┘
                     │
                     ▼
      ┌─────────────────────────────┐
      │         Redis Cache         │
      │    check cached score       │
      └──────────────┬──────────────┘
          cache hit  │   cache miss
                     │
                     ▼
              ┌───────────────┐
              │     Queue     │
              └───────┬───────┘
                      │
                      ▼
      ┌─────────────────────────────┐
      │     Background Worker       │
      │     TokenBucket limiter     │
      │        100 req/sec          │
      └──────────────┬──────────────┘
                     │
                     ▼
      ┌─────────────────────────────┐
      │   IsolationForest Model     │
      │     (Anomaly Detection)     │
      └──────────────┬──────────────┘
                     │
                     ▼
      ┌─────────────────────────────┐
      │         Redis Cache         │
      │      store anomaly score    │
      └──────────────┬──────────────┘
                     │
                     ▼
      ┌─────────────────────────────┐
      │      Decision Engine        │
      │ allow / alert / block       │
      └──────────────┬──────────────┘
                     │
                     ▼
      ┌─────────────────────────────┐
      │     Connection Storage      │
      │      (final decision)       │
      └─────────────────────────────┘
```


---

# Architectural Components and Their Role in Scalability and AI Constraints

## AI Gateway — submit_for_scoring()

Receives connections that require AI scoring and submits them asynchronously.
Prevents blocking the API and allows the system to handle high traffic safely.

---

## Redis Cache — check cached score

Checks whether an anomaly score already exists for a similar connection.
Reduces unnecessary model calls and helps stay within the 100 req/sec AI limit.

---

## Queue

Buffers incoming connections waiting for AI scoring.
Allows the system to absorb bursts up to 1000 req/sec without dropping requests.

---

## Background Worker + TokenBucket limiter (100 req/sec)

Processes queued connections asynchronously using a controlled rate.
Ensures the AI scoring service never exceeds its hard limit of 100 requests/sec.

---

## IsolationForest Model (Anomaly Detection)

Computes anomaly scores to detect suspicious network connections.
Provides the AI-based decision input required for allow, alert, or block actions.

---

## Redis Cache — store anomaly score

Stores anomaly scores after model evaluation.
Improves performance by enabling reuse of results and reducing model load.

---

## Connection and Policy Storage

Stores connection data, policies, and final security decisions.
Enables policy evaluation and allows retrieving decisions via the API.

---


## How to run the code (locally or via script)

### 1. Create a virtual environment

```cmd
py -m venv .venv
```

---

### 2. Activate the virtual environment

```cmd
.venv\Scripts\activate
```

---

### 3. Install dependencies

```cmd
pip install -r requirements.txt
```

---

### 4. Start the server

```cmd
uvicorn app.main:app --reload
```

---

### 5. Verify the server is running

You should see:

```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

### 6. Open the API documentation

Open your browser and go to:

```
http://127.0.0.1:8000/docs
```

From there you can test:

* POST /connections
* POST /policies
* GET /connections/{id}
* PUT /policies/{policy_id}

---

### 7. Run Load Test (Optional – Performance Simulation)

In a separate terminal window, run:

```cmd
python scripts\load_test.py
```

This simulates high traffic and validates queue buffering, rate limiting, and AI scoring behavior.

## Tests

Basic API integration tests are included using pytest.

Run tests:

pytest

---

## Design Summary and Key Decisions

The system is designed to separate policy evaluation from AI anomaly scoring to ensure fast response times and scalability.

Key design decisions:

- Policies are evaluated synchronously for immediate allow/block decisions without invoking AI scoring unnecessarily.
- AI scoring is handled asynchronously via a queue and background worker to prevent blocking incoming requests.
- Redis is used as a cache layer to store anomaly scores and reduce repeated model evaluations.
- A TokenBucket rate limiter ensures the AI scoring service respects the hard limit of 100 requests/sec.
- Connection and policy storage are separated to allow independent scaling and clean architecture boundaries.

This architecture allows the system to handle burst traffic up to 1000 requests/sec while respecting AI scoring constraints.

---

## Anomaly Scoring Approach

An IsolationForest model is used to detect anomalous network connections.

The model evaluates connection features and produces an anomaly score, which is normalized to a range of 0 to 1.

The score is used to determine the final decision:

- score > 0.8 → block
- score 0.5–0.8 → alert
- score < 0.5 → allow (if no blocking policy exists)

To ensure scalability, anomaly scoring is performed asynchronously using a background worker and cached in Redis to avoid repeated evaluations.

---

## Limitations and Future Improvements

Current limitations:

- Connection and policy storage use in-memory storage and Redis instead of a persistent database.
- The IsolationForest model is trained on simulated data and not production network traffic.
- The system runs as a single instance and does not include horizontal scaling.

Future improvements:

- Replace in-memory storage with a persistent database such as PostgreSQL.
- Deploy multiple worker instances behind a distributed queue for higher throughput.
- Add monitoring, metrics, and alerting for production environments.
- Support model retraining and versioning.
- Deploy using Docker and Kubernetes for production scalability.

---

## Example Requests (CMD / curl)

These examples demonstrate policy creation, connection submission, and AI-based anomaly detection.

---

### 1. Create Policy

Create a security policy that blocks traffic from a specific source IP to destination port 443.

```cmd
curl -X POST http://127.0.0.1:8000/policies ^
-H "Content-Type: application/json" ^
-d "{\"policy_id\":\"P-002\",\"conditions\":[{\"field\":\"destination_port\",\"operator\":\"==\",\"value\":\"443\"},{\"field\":\"source_ip\",\"operator\":\"==\",\"value\":\"192.168.1.10\"}],\"action\":\"block\"}"
```

Response:

```json
{"message":"policy created"}
```

---

### 2. Update Policy

Update an existing policy.

```cmd
curl -X PUT http://127.0.0.1:8000/policies/P-002 ^
-H "Content-Type: application/json" ^
-d "{\"conditions\":[{\"field\":\"destination_port\",\"operator\":\"==\",\"value\":\"443\"},{\"field\":\"source_ip\",\"operator\":\"==\",\"value\":\"192.168.1.10\"}],\"action\":\"block\"}"
```

Response:

```json
{"message":"policy updated"}
```

---

### 3. Submit Connection – Policy Match Case

Submit a connection that matches the policy. The decision is applied immediately without AI scoring.

```cmd
curl -X POST http://127.0.0.1:8000/connections ^
-H "Content-Type: application/json" ^
-d "{\"source_ip\":\"192.168.1.10\",\"destination_ip\":\"10.0.0.5\",\"destination_port\":443,\"protocol\":\"TCP\",\"timestamp\":\"2025-04-30T12:34:56Z\"}"
```

Response:

```json
{
  "connection_id":"aad6ede9-a86a-4a9e-b1fa-1dd4a20e2bf9",
  "decision":"block",
  "anomaly_score":null,
  "matched_policy":"P-TEST",
  "pending_ai":false
}
```

Explanation:

* The connection matched an existing policy
* The connection was blocked immediately
* No AI scoring was required

---

### 4. Submit Connection – AI Scoring Case

Submit a connection that does not match any policy. The connection is sent for asynchronous AI scoring.

```cmd
curl -X POST http://127.0.0.1:8000/connections ^
-H "Content-Type: application/json" ^
-d "{\"source_ip\":\"1.1.1.1\",\"destination_ip\":\"8.8.8.8\",\"destination_port\":8888,\"protocol\":\"TCP\",\"timestamp\":\"2025-04-30T12:40:00Z\"}"
```

Immediate Response:

```json
{
  "connection_id":"ea462f7a-c9ad-4ec8-a15b-9c647c1a0fc0",
  "decision":"alert",
  "anomaly_score":null,
  "matched_policy":null,
  "pending_ai":true
}
```

Explanation:

* No policy matched
* The connection was submitted for background AI scoring
* The API returned immediately

---

### 5. Retrieve Connection Decision After AI Scoring

Retrieve the final decision after AI processing completes.

```cmd
curl http://127.0.0.1:8000/connections/ea462f7a-c9ad-4ec8-a15b-9c647c1a0fc0
```

Response:

```json
{
  "connection_id":"ea462f7a-c9ad-4ec8-a15b-9c647c1a0fc0",
  "decision":"alert",
  "anomaly_score":0.5405642501558188,
  "matched_policy":null,
  "pending_ai":false,
  "source_ip":"1.1.1.1",
  "destination_ip":"8.8.8.8",
  "destination_port":8888,
  "protocol":"TCP",
  "timestamp":"2025-04-30 12:40:00+00:00"
}
```

Explanation:

* AI scoring completed successfully
* anomaly_score was calculated
* The final decision was stored and returned

---