
## Plan: Enhanced Status Bar Feedback & Status Log

To improve user experience, we will enhance the status bar in Vector Inspector to display real-time feedback for key actions (e.g., semantic search, data loading, clustering). This includes showing operation status, result counts, and elapsed time (e.g., "Search complete – 28 results in 0.43s").

Additionally, we will keep a log of all status updates, enabling a future feature where users can view a history of recent status messages (e.g., via a menu or dialog). This log will be maintained in memory (with a configurable length) and optionally persisted for session review.

The plan will ensure consistency, minimal UI disruption, and easy extensibility for future actions and features.

**Steps**

### Phase 1: Discovery & Design
1. Identify all current actions that would benefit from status bar feedback (semantic search, data load, clustering, etc.).
2. Review how the status bar is currently updated in the UI layer (likely in `src/vector_inspector/ui/`).
3. Determine if there is a centralized status bar update utility or if updates are scattered.
4. Decide on a standard message format (e.g., "Action complete – X results in Ys").
5. Define a timing mechanism (start/stop timer per action) that is easy to integrate.


### Phase 2: Implementation
6. Refactor or introduce a utility function/class for status bar updates, supporting:
   - Message formatting (with placeholders for action, result count, elapsed time)
   - Optional: message type (info, warning, error)
   - **Status log recording:** Each status update is appended to an in-memory log (with a configurable max length, e.g., 100 entries). Optionally, add a method to retrieve or clear the log.
7. For each key action (starting with semantic search):
   - Add timing logic (start timer at action start, stop at completion)
   - On completion, call the status bar update utility with result count and elapsed time
   - The status log is updated with each message.
8. Ensure all status bar updates are routed through the new utility for consistency and logging.
9. Add extensibility hooks for future actions and for exposing the log to the UI (for a future feature).

### Phase 3: Verification
10. Manually test each action to confirm:
    - Status bar updates appear at the right time
    - Message format is clear and consistent
    - Elapsed time is accurate and result count is correct
11. (Optional) Add automated UI tests if feasible for status bar messages.

**Relevant files**
- `src/vector_inspector/ui/views/` — likely where main actions are triggered and status bar is updated
- `src/vector_inspector/ui/components/` — reusable widgets, possibly status bar logic
- `src/vector_inspector/services/` — where business logic actions (search, clustering) are called
- Any existing status bar utility or helper

**Verification**
1. Trigger semantic search and other key actions; observe status bar for correct, timely messages.
2. Confirm elapsed time and result count are accurate.
3. Review code to ensure all status bar updates use the new utility.
4. (Optional) Peer review for message clarity and code extensibility.

**Decisions**
- All status bar updates will use a single utility for consistency.
- Message format: "Action complete – X results in Ys" (customizable per action).
- Only user-visible, time-consuming actions will trigger these messages.


**Further Considerations**
1. Should status bar messages auto-clear after a timeout, or persist until the next action? (Recommend: auto-clear after 5–10s, but allow override.)
2. Should errors/warnings use a different color or icon in the status bar? (Recommend: yes, for clarity.)
3. Should this be extensible for plugin actions in the future? (Recommend: yes, design utility for easy extension.)
4. **Status log UI:** In a future feature, provide a menu or dialog to let users view the recent status log, copy entries, or clear the log. Consider privacy and memory usage for long sessions.
