from datetime import datetime, timedelta
from flask import Blueprint, jsonify, render_template, request
from CTFd.models import Users, db
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.user import get_current_user
from CTFd.plugins.ctfd_compose.models import ComposeChallenge, ComposeContainer
from CTFd.plugins.ctfd_compose.utils.docker_compose import (
    allocate_port,
    compose_down,
    compose_rebuild,
    compose_restart,
    compose_up,
    generate_flag,
    get_public_host,
    list_available_challenges,
)

compose_api = Blueprint("compose_api", __name__, template_folder="templates")


def format_container_data(container: ComposeContainer, challenge: ComposeChallenge):
    now = datetime.utcnow()
    remaining = max(0, int((container.expires_at - now).total_seconds()))
    host = get_public_host()

    if challenge.redirect_type == "http":
        conn_str = f"http://{host}:{container.port}"
    else:
        conn_str = f"nc {host} {container.port}"

    return {
        "status": "running",
        "container_id": container.id,
        "challenge_id": challenge.id,
        "challenge_name": challenge.name,
        "host": host,
        "port": container.port,
        "redirect_type": challenge.redirect_type,
        "connection": conn_str,
        "remaining_time": remaining,
        "expires_at": container.expires_at.isoformat(),
        "renew_count": container.renew_count,
        "max_renew": challenge.max_renew,
        "renews_left": max(0, challenge.max_renew - container.renew_count),
    }


# ==========================================
# Contestant API Routes
# ==========================================

@compose_api.route("/api/v1/plugins/ctfd_compose/container", methods=["GET"])
@authed_only
def get_container():
    user = get_current_user()
    challenge_id = request.args.get("challenge_id", type=int)

    if not challenge_id:
        return jsonify({"success": False, "message": "Missing challenge_id"}), 400

    challenge = ComposeChallenge.query.filter_by(id=challenge_id).first()
    if not challenge:
        return jsonify({"success": False, "message": "Challenge not found"}), 404

    container = ComposeContainer.query.filter_by(
        user_id=user.id,
        challenge_id=challenge_id,
        status="running",
    ).first()

    if not container:
        return jsonify({"success": True, "data": {"status": "stopped"}})

    now = datetime.utcnow()
    if container.expires_at <= now:
        # Expired - clean up
        try:
            compose_down(container.project_name, container.compose_dir)
        except Exception:
            pass
        db.session.delete(container)
        db.session.commit()
        return jsonify({"success": True, "data": {"status": "stopped"}})

    return jsonify({"success": True, "data": format_container_data(container, challenge)})


@compose_api.route("/api/v1/plugins/ctfd_compose/container", methods=["POST"])
@authed_only
def start_container():
    user = get_current_user()
    data = request.get_json() or request.form or {}
    challenge_id = data.get("challenge_id") or request.args.get("challenge_id", type=int)

    if not challenge_id:
        return jsonify({"success": False, "message": "Missing challenge_id"}), 400

    challenge = ComposeChallenge.query.filter_by(id=challenge_id).first()
    if not challenge:
        return jsonify({"success": False, "message": "Challenge not found"}), 404

    if not challenge.compose_dir:
        return jsonify({"success": False, "message": "Challenge has no compose directory configured"}), 400

    # Check if user already has this container running
    existing = ComposeContainer.query.filter_by(
        user_id=user.id,
        challenge_id=challenge.id,
        status="running",
    ).first()

    if existing:
        if existing.expires_at > datetime.utcnow():
            return jsonify({
                "success": True,
                "data": format_container_data(existing, challenge),
                "message": "Container already running",
            })
        else:
            # Clean expired
            try:
                compose_down(existing.project_name, existing.compose_dir)
            except Exception:
                pass
            db.session.delete(existing)
            db.session.commit()

    # Limit to 1 active container across all challenges per user to prevent resource exhaustion
    active_other = ComposeContainer.query.filter_by(
        user_id=user.id,
        status="running",
    ).first()

    if active_other:
        # Automatically clean up previously running container for this user
        try:
            compose_down(active_other.project_name, active_other.compose_dir)
        except Exception:
            pass
        db.session.delete(active_other)
        db.session.commit()

    try:
        port = allocate_port()
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to allocate port: {str(e)}"}), 500

    flag = generate_flag(challenge.flag_template) if challenge.dynamic_flag else "CTF{static_flag}"
    project_name = f"ctfd_c{challenge.id}_u{user.id}"

    success, output = compose_up(
        project_name=project_name,
        compose_dir=challenge.compose_dir,
        port=port,
        flag=flag,
    )

    if not success:
        return jsonify({"success": False, "message": f"Docker compose failed: {output}"}), 500

    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=challenge.timeout)

    container = ComposeContainer(
        user_id=user.id,
        challenge_id=challenge.id,
        project_name=project_name,
        compose_dir=challenge.compose_dir,
        port=port,
        flag=flag,
        start_time=now,
        expires_at=expires_at,
        renew_count=0,
        status="running",
    )
    db.session.add(container)
    db.session.commit()

    return jsonify({
        "success": True,
        "data": format_container_data(container, challenge),
        "message": "Container successfully launched!",
    })


@compose_api.route("/api/v1/plugins/ctfd_compose/container", methods=["PATCH"])
@authed_only
def renew_container():
    user = get_current_user()
    data = request.get_json() or request.form or {}
    challenge_id = data.get("challenge_id") or request.args.get("challenge_id", type=int)

    if not challenge_id:
        return jsonify({"success": False, "message": "Missing challenge_id"}), 400

    challenge = ComposeChallenge.query.filter_by(id=challenge_id).first()
    if not challenge:
        return jsonify({"success": False, "message": "Challenge not found"}), 404

    container = ComposeContainer.query.filter_by(
        user_id=user.id,
        challenge_id=challenge.id,
        status="running",
    ).first()

    if not container:
        return jsonify({"success": False, "message": "No active container found"}), 404

    if container.renew_count >= challenge.max_renew:
        return jsonify({
            "success": False,
            "message": f"Maximum renewals reached ({challenge.max_renew}/{challenge.max_renew})",
        }), 400

    # Extend by 10 minutes (or half of total timeout, whichever is smaller)
    extension_seconds = max(300, min(600, challenge.timeout))
    container.expires_at = container.expires_at + timedelta(seconds=extension_seconds)
    container.renew_count += 1
    db.session.commit()

    return jsonify({
        "success": True,
        "data": format_container_data(container, challenge),
        "message": f"Container extended by {extension_seconds // 60} minutes!",
    })


@compose_api.route("/api/v1/plugins/ctfd_compose/container", methods=["DELETE"])
@authed_only
def destroy_container():
    user = get_current_user()
    data = request.get_json() or request.form or {}
    challenge_id = data.get("challenge_id") or request.args.get("challenge_id", type=int)

    if not challenge_id:
        return jsonify({"success": False, "message": "Missing challenge_id"}), 400

    container = ComposeContainer.query.filter_by(
        user_id=user.id,
        challenge_id=challenge_id,
        status="running",
    ).first()

    if not container:
        return jsonify({"success": True, "message": "Container already stopped."})

    success, output = compose_down(container.project_name, container.compose_dir)
    db.session.delete(container)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Container has been destroyed successfully.",
    })


# ==========================================
# Admin API & Page Routes
# ==========================================

@compose_api.route("/admin/compose", methods=["GET"])
@admins_only
def admin_page():
    return render_template("admin_containers.html")


@compose_api.route("/api/v1/plugins/ctfd_compose/admin/containers", methods=["GET"])
@admins_only
def admin_list_containers():
    containers = ComposeContainer.query.filter_by(status="running").all()
    results = []
    now = datetime.utcnow()

    for c in containers:
        user = Users.query.filter_by(id=c.user_id).first()
        challenge = ComposeChallenge.query.filter_by(id=c.challenge_id).first()
        remaining = max(0, int((c.expires_at - now).total_seconds()))

        results.append({
            "id": c.id,
            "project_name": c.project_name,
            "user_id": c.user_id,
            "username": user.name if user else f"User #{c.user_id}",
            "challenge_id": c.challenge_id,
            "challenge_name": challenge.name if challenge else f"Chall #{c.challenge_id}",
            "compose_dir": c.compose_dir,
            "port": c.port,
            "flag": c.flag,
            "start_time": c.start_time.isoformat() if c.start_time else None,
            "expires_at": c.expires_at.isoformat() if c.expires_at else None,
            "remaining_time": remaining,
            "renew_count": c.renew_count,
            "status": c.status,
        })

    return jsonify({"success": True, "data": results})


@compose_api.route("/api/v1/plugins/ctfd_compose/admin/containers/restart", methods=["POST"])
@admins_only
def admin_restart_container():
    data = request.get_json() or {}
    container_id = data.get("container_id")
    container = ComposeContainer.query.filter_by(id=container_id).first()

    if not container:
        return jsonify({"success": False, "message": "Container not found"}), 404

    success, output = compose_restart(
        project_name=container.project_name,
        compose_dir=container.compose_dir,
        port=container.port,
        flag=container.flag,
    )

    if not success:
        return jsonify({"success": False, "message": f"Restart failed: {output}"}), 500

    return jsonify({"success": True, "message": f"Container {container.project_name} restarted successfully."})


@compose_api.route("/api/v1/plugins/ctfd_compose/admin/containers/rebuild", methods=["POST"])
@admins_only
def admin_rebuild_container():
    data = request.get_json() or {}
    container_id = data.get("container_id")
    container = ComposeContainer.query.filter_by(id=container_id).first()

    if not container:
        return jsonify({"success": False, "message": "Container not found"}), 404

    success, output = compose_rebuild(
        project_name=container.project_name,
        compose_dir=container.compose_dir,
        port=container.port,
        flag=container.flag,
    )

    if not success:
        return jsonify({"success": False, "message": f"Rebuild failed: {output}"}), 500

    return jsonify({"success": True, "message": f"Container {container.project_name} rebuilt and started successfully."})


@compose_api.route("/api/v1/plugins/ctfd_compose/admin/containers", methods=["DELETE"])
@admins_only
def admin_destroy_container():
    data = request.get_json() or {}
    container_id = data.get("container_id")
    container = ComposeContainer.query.filter_by(id=container_id).first()

    if not container:
        return jsonify({"success": False, "message": "Container not found"}), 404

    try:
        compose_down(container.project_name, container.compose_dir)
    except Exception:
        pass

    db.session.delete(container)
    db.session.commit()

    return jsonify({"success": True, "message": f"Container {container.project_name} stopped and deleted."})


@compose_api.route("/api/v1/plugins/ctfd_compose/admin/challenges-dirs", methods=["GET"])
@admins_only
def admin_get_challenge_dirs():
    dirs = list_available_challenges()
    return jsonify({"success": True, "data": dirs})
