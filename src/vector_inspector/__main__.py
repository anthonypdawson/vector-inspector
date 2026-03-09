if __name__ == "__main__":
    from vector_inspector._cli import parse_cli_args

    # Handle --version / --help / --llm-console before importing Qt/GUI modules.
    # --llm-console sets VI_LLM_CONSOLE=1 which main.py picks up to also show
    # the LLM debug window alongside the normal application window.
    parse_cli_args()

    from vector_inspector.main import main

    main()
