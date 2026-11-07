
import uvicorn

from forge.dashboard.app import create_configured_app


def main():
    app = create_configured_app()

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
    )


if __name__ == "__main__":
    main()
