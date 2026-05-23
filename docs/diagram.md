flowchart LR
  %% Entrypoints
  CLI["CLI\nvector_inspector._cli:console_entry"] --> MAIN["GUI entry\nvector_inspector/main.py:main()"]
  MODMAIN["python -m vector_inspector\n__main__.py"] --> MAIN

  %% Startup + shell
  MAIN --> QT["QApplication\n(PySide6)"]
  MAIN --> TEL["TelemetryService\nservices/telemetry_service.py"]
  MAIN --> MW["MainWindow\nui/main_window.py"]

  %% Composition root creates shared services/state
  MW --> SHELL["InspectorShell\nui/main_window_shell.py"]
  MW --> STATE["AppState\nstate/app_state.py"]
  MW --> TR["ThreadedTaskRunner\nservices/task_runner.py"]
  MW --> CM["ConnectionManager\ncore/connection_manager.py"]
  MW --> PS["ProfileService\nservices/profile_service.py"]
  MW --> SS["SettingsService\nservices/settings_service.py"]
  MW --> CC["ConnectionController\nui/controllers/connection_controller.py"]

  %% Providers / connections
  CC --> PF["ProviderFactory\ncore/provider_factory.py"]
  PF --> DB["VectorDBConnection impls\ncore/connections/*"]
  CM --> CI["ConnectionInstance\n(wrapper/forwarder)"]
  CI --> DB

  %% UI tabs (views subscribe to AppState)
  MW --> TABS["InspectorTabs\nui/tabs.py"]
  TABS --> INFO["InfoPanel\nui/views/info_panel.py"]
  TABS --> META["MetadataView\nui/views/metadata_view.py"]
  TABS --> SEARCH["SearchView\nui/views/search_view.py"]
  TABS --> VIZ["VisualizationView\nui/views/visualization_view.py\n(lazy-loaded)"]

  INFO --> STATE
  META --> STATE
  SEARCH --> STATE
  VIZ --> STATE

  %% Typical view-to-provider work
  SEARCH --> SR["SearchRunner\nservices/search_runner.py"]
  SR --> CI
  META --> LOAD["Data loaders / collection services\nservices/*"]
  LOAD --> CI

  %% Extension hooks
  SEARCH --> EXT["Extensions hooks\nextensions/__init__.py\n(table context menu, settings panels)"]
  META --> EXT
  MW --> EXT
