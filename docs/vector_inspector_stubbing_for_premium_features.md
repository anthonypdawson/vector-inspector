# Qt UI Ownership and Plugin Architecture  
Vector Inspector (VI) is the UI shell and engine.  
Vector Studio (VS) is the plugin layer that activates premium workflows.

VI owns all UI elements.  
VS owns all premium behavior.  
No UI duplication. No premium logic in VI. No UI creation in VS.

---

## Vector Inspector Responsibilities

- Defines every QAction, QMenu, QMenuItem, QToolButton, QDockWidget, QWidget.
- Renders all right‑click menus and toolbar items.
- Creates disabled “Premium / Requires Vector Studio” stubs.
- Connects premium UI elements to a no‑op stub.
- Contains zero premium logic.

### Disabled Stub Pattern (VI)

```python
# In Vector Inspector UI setup

self.action_view_similar = QAction("View Similar", self)
self.action_view_similar.setObjectName("action_view_similar")
self.action_view_similar.setEnabled(False)
self.action_view_similar.setToolTip("Requires Vector Studio")

context_menu.addAction(self.action_view_similar)

self.action_view_similar.triggered.connect(self.premium_stub)

def premium_stub(self):
    QMessageBox.information(
        self,
        "Premium Feature",
        "This feature requires Vector Studio."
    )


---
Vector Studio Responsibilities
• Never creates UI controls.
• Never duplicates menu entries.
• Never modifies VI layout.
• Locates existing VI controls.
• Enables them.
• Removes the stub connection.
• Injects the real premium workflow.
# Behavior Injection Pattern (VS)

# In Vector Studio initialization

def activate_premium_features(self, inspector):
    action = inspector.findChild(QAction, "action_view_similar")
    if not action:
        return

    action.setEnabled(True)
    action.setToolTip("")

    try:
        action.triggered.disconnect()
    except Exception:
        pass

    action.triggered.connect(self.open_view_similar_workflow)

def open_view_similar_workflow(self):
    # Full Studio-only implementation
    pass

---

Absolute Rules
• VI owns UI.
• VS owns premium behavior.
• No UI duplication.
• No premium logic in VI.
• No UI creation in VS.
This keeps the architecture stable, predictable, and plugin‑friendly.
