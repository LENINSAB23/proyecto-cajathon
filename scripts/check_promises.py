from app import app
from routes.promesas import _refresh_statuses


def main():
    with app.app_context():
        _refresh_statuses()


if __name__ == "__main__":
    main()
