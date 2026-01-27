# Latest updates

## Vector Inspector 2026.01 Release Notes

### Major Refactor and Studio-Ready Architecture
- Refactored main window into modular components:
  - InspectorShell: reusable UI shell (splitter, tabs, layout)
  - ProviderFactory: centralized connection creation
  - DialogService: dialog management
  - ConnectionController: connection lifecycle and threading
  - InspectorTabs: pluggable tab registry
- MainWindow now inherits from InspectorShell and is fully reusable as a widget
- Bootstrap logic is separated from UI logic—Studio can host Inspector as a component
- Tab system is now pluggable: Studio and Inspector can add, remove, or override tabs via TabDefinition
- All Inspector UI logic is self-contained; Studio can extend without modifying Inspector code

### Data Browser Improvements
- Added a checkbox: Generate embeddings on edit (default: checked)
  - When unchecked, editing a row skips embedding regeneration
  - Setting is persisted per user

### Developer and Architecture Notes
- All modules pass syntax checks and are ready for Studio integration
- No breaking changes for existing Inspector users
- Inspector is now a true UI module, not just an application

---

