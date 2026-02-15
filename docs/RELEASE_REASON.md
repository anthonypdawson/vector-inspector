## Release Notes (0.4.0)

### Major Features

#### Inline Details Pane
- **New collapsible bottom panel** in both Metadata Browser and Search views
- Shows selected item details without opening a modal dialog
- Includes:
  - Header bar with ID, timestamp, dimensions, and cluster info
  - Document preview with scrollable text
  - Collapsible metadata section (JSON formatted)
  - Collapsible vector embedding section with copy buttons
  - Search-specific metrics (rank, similarity score) in Search view
- State persistence: remembers splitter sizes and section collapse states across sessions
- Auto-hides in Search view when no results are selected
- Dark theme optimized with proper contrast throughout

### UI/UX Improvements

#### Metadata Browser
- **Double-click behavior changed**: Now opens read-only "View Details" dialog (consistent with right-click → View Details)
- **Edit functionality**: Moved to right-click context menu only for more intentional editing workflow
- Inline details pane provides quick access to item information without modal dialogs

#### Search View
- **Inline details pane** shows search-specific metrics (rank, distance, similarity)
- **Reduced search input height** from 100px to 60px for more compact layout
- **Advanced Metadata Filters** now properly collapse when unchecked, saving vertical space
- **Improved layout**: Query section content hugs top, giving more room to results table and details pane
- Details pane automatically hides when no results are selected

### Technical Improvements
- New reusable `CollapsibleSection` widget for expandable UI sections
- New `InlineDetailsPane` component with dual mode support (data_browser/search)
- Settings service integration for UI state persistence
- Dark theme color palette applied consistently across new components

---