import uvicorn

from app.config import setup
from app.main import create_app

def main() -> None:
    config = setup()
    uvicorn.run(
        create_app(config),
        host=config.service.host,
        port=config.service.port,
    )

if __name__ == "__main__":
    main()