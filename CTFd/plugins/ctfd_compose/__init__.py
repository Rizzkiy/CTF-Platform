import threading
import time
from datetime import datetime
from CTFd.models import db
from CTFd.plugins import register_admin_plugin_menu_bar, register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES
from CTFd.plugins.ctfd_compose.api import compose_api
from CTFd.plugins.ctfd_compose.challenge_type import ComposeChallengeType
from CTFd.plugins.ctfd_compose.models import ComposeChallenge, ComposeContainer
from CTFd.plugins.ctfd_compose.utils.docker_compose import compose_down


def start_expiry_worker(app):
    """
    Background worker that runs every 15 seconds to destroy expired containers.
    """
    def worker():
        while True:
            time.sleep(15)
            try:
                with app.app_context():
                    now = datetime.utcnow()
                    expired = ComposeContainer.query.filter(
                        ComposeContainer.expires_at <= now,
                        ComposeContainer.status == "running"
                    ).all()

                    for c in expired:
                        try:
                            compose_down(c.project_name, c.compose_dir)
                        except Exception as e:
                            app.logger.error(f"[ctfd_compose] Error cleaning container {c.project_name}: {e}")
                        db.session.delete(c)

                    if expired:
                        db.session.commit()
            except Exception:
                pass

    thread = threading.Thread(target=worker, daemon=True, name="compose_expiry_worker")
    thread.start()


def load(app):
    # 1. Create database tables if they do not exist
    with app.app_context():
        app.db.create_all()

    # 2. Register Challenge Type
    CHALLENGE_CLASSES["compose"] = ComposeChallengeType

    # 3. Register Plugin Assets
    register_plugin_assets_directory(app, base_path="/plugins/ctfd_compose/assets/")

    # 4. Register API & Admin Blueprint
    app.register_blueprint(compose_api)

    # 5. Register Admin Panel Navigation Item
    register_admin_plugin_menu_bar("Compose Containers", "/admin/compose")

    # 6. Start Expiration Background Cleaner
    start_expiry_worker(app)

    print(" * [ctfd_compose] Dynamic Docker Compose plugin initialized successfully.")
