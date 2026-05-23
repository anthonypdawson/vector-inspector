# 🐛 Vector Inspector — Telemetry‑Derived Bug List

## 1. Duplicate `session.start` Events
**Evidence:** Two `session.start` events fired within ~40 ms.  
**Impact:** Inflates analytics, indicates race condition.  
**Severity:** Medium.

## 2. `db_type` Reported as `"unknown"` During Search
**Evidence:** `query.executed` event shows `"db_type": "unknown"`.  
**Impact:** Breaks provider‑level analytics and debugging.  
**Severity:** High.

## 3. Ingestion Failure (1/1 Failed, 0 Chunks Written)
**Evidence:** `ingestion.completed` → `"failed": 1`, `"chunks_written": 0`, `"duration_ms": 151491`.  
**Impact:** Core feature failure; user waited 2.5 minutes for nothing.  
**Severity:** Critical.

## 4. Table View Opens Repeatedly With 0 Rows / 0 Columns
**Evidence:** Multiple `ui.table_view_opened` events with `"row_count": 0`, `"column_count": 0"`.  
**Impact:** Confusing UX; may indicate repeated render loop or missing metadata.  
**Severity:** Medium.
1
## 5. Search Tab Re‑Fires Multiple Times
**Evidence:** Several `ui.search_tab_opened` events within 1–2 seconds.  
**Impact:** Suggests double‑firing or user retrying due to unclear state.  
**Severity:** Low–Medium.

## 6. Visualization Opens With No Data
**Evidence:** `"point_count": 0`, `"embedding_dim": null"`.  
**Impact:** Visualization tab appears broken when no collection is selected.  
**Severity:** Medium.

## 7. Repeated DB Connection Attempts
**Evidence:** Dozens of `db.connection_attempt` events in short bursts.  
**Impact:** Telemetry noise; may indicate reconnection loop or unclear UI state.  
**Severity:** Medium.

## 8. Search Latency Spike (1138 ms) on Empty Collection
**Evidence:** `query.executed` → `"latency_ms": 1138"`.  
**Impact:** Makes app feel slow even when no data exists.  
**Severity:** Medium.

## 9. Session ID Reused Across App Launches
**Evidence:** `app_launch` includes a pre‑existing `session_id`.  
**Impact:** Breaks session analytics; indicates state not reset on launch.  
**Severity:** Medium.


# 🔒 Recommendation: Lock Down Tabs Until a Collection Is Selected

## Problem
Telemetry shows users repeatedly:
- Opening **Search** with no collection selected  
- Opening **Visualization** with no embeddings  
- Opening **Data/Table View** with 0 rows / 0 columns  
- Refreshing collections multiple times  
- Running searches on empty collections  

This creates confusion and generates misleading telemetry.

## Solution
Lock the following tabs until a collection is selected:
- **Data**
- **Search**
- **Visualization**

## UX Behavior
When no collection is selected, show a clear empty‑state panel:
- “Select a collection to begin”
- “Choose a collection from the sidebar”
- “No collection selected”

## Benefits
- Prevents meaningless actions  
- Reduces user confusion  
- Reduces telemetry noise  
- Prevents search/visualization errors  
- Makes the app feel more intentional and polished  