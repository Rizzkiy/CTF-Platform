import os
import random
import secrets
import socket
import subprocess
import logging
from flask import request, current_app
from CTFd.utils import get_config

logger = logging.getLogger("ctfd-compose")

BASE_CHALLENGES_DIR = os.environ.get("CHALLENGES_DIR", "/challenges")
COMPOSE_FILE_NAMES = [
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
]


def get_compose_file_path(compose_dir: str):
    """
    Given a directory name inside BASE_CHALLENGES_DIR, finds the compose file.
    """
    dir_path = os.path.join(BASE_CHALLENGES_DIR, compose_dir)
    if not os.path.isdir(dir_path):
        return None, None

    for fname in COMPOSE_FILE_NAMES:
        fpath = os.path.join(dir_path, fname)
        if os.path.isfile(fpath):
            return dir_path, fpath

    return None, None


def list_available_challenges():
    """
    Scans BASE_CHALLENGES_DIR and returns all directories that contain a docker-compose file.
    """
    if not os.path.isdir(BASE_CHALLENGES_DIR):
        return []

    results = []
    try:
        entries = sorted(os.listdir(BASE_CHALLENGES_DIR))
        for entry in entries:
            dir_path = os.path.join(BASE_CHALLENGES_DIR, entry)
            if os.path.isdir(dir_path):
                for fname in COMPOSE_FILE_NAMES:
                    if os.path.isfile(os.path.join(dir_path, fname)):
                        results.append(entry)
                        break
    except Exception as e:
        logger.error(f"Error scanning challenges directory: {e}")

    return results


def is_port_available(port: int) -> bool:
    """
    Check if a port is available on the host/network.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", port))
        if socket.has_ipv6:
            try:
                with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s6:
                    s6.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s6.bind(("::", port))
            except socket.error:
                return False
        return True
    except socket.error:
        return False


def allocate_port(min_port: int = 30000, max_port: int = 40000, max_attempts: int = 50) -> int:
    """
    Allocates an unused port within range.
    Checks both DB registered active ports and socket binding.
    """
    from flask import has_app_context

    used_ports = set()
    if has_app_context():
        from CTFd.plugins.ctfd_compose.models import ComposeContainer
        try:
            active_containers = ComposeContainer.query.filter_by(status="running").all()
            used_ports = {c.port for c in active_containers if c.port}
        except Exception:
            pass

    available_candidates = [p for p in range(min_port, max_port) if p not in used_ports]
    if not available_candidates:
        raise RuntimeError("No available ports left in the configured range")

    # Shuffle to distribute port usage
    random.shuffle(available_candidates)

    for port in available_candidates[:max_attempts]:
        if is_port_available(port):
            return port

    raise RuntimeError("Could not find an open host port after multiple checks")


def generate_flag(template: str = "CTF{compose_{token}}") -> str:
    """
    Generates dynamic flag from template.
    """
    token = secrets.token_hex(12)
    if not template:
        template = "CTF{compose_{token}}"

    if "{token}" in template:
        return template.replace("{token}", token)
    else:
        # If template doesn't contain {token}, format cleanly
        if template.endswith("}"):
            return f"{template[:-1]}_{token}}}"
        return f"{template}_{token}"


def get_public_host():
    """
    Determines public host or domain for contestants to access their container.
    """
    configured_host = get_config("compose_host")
    if configured_host:
        return configured_host.strip()

    # Fallback to request host (without port)
    if request:
        req_host = request.host.split(":")[0]
        if req_host in ("localhost", "127.0.0.1"):
            return "127.0.0.1"
        return req_host

    return "127.0.0.1"


def run_compose_command(project_name: str, compose_dir: str, command: list, env_vars: dict = None, timeout: int = 180):
    """
    Runs a docker compose command with project name and directory isolation.
    """
    dir_path, compose_file = get_compose_file_path(compose_dir)
    if not compose_file:
        return False, f"Compose directory '{compose_dir}' or docker-compose.yml not found in {BASE_CHALLENGES_DIR}"

    cmd = [
        "docker",
        "compose",
        "-p",
        project_name,
        "--project-directory",
        dir_path,
        "-f",
        compose_file,
    ] + command

    env = os.environ.copy()
    if env_vars:
        for k, v in env_vars.items():
            env[k] = str(v)

    logger.info(f"Executing: {' '.join(cmd)} (project: {project_name})")

    try:
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            timeout=timeout,
        )
        if res.returncode == 0:
            return True, res.stdout
        else:
            err_msg = res.stderr or res.stdout
            logger.error(f"Compose error ({res.returncode}): {err_msg}")
            return False, err_msg
    except subprocess.TimeoutExpired:
        logger.error(f"Compose command timed out after {timeout}s: {' '.join(cmd)}")
        return False, f"Command timed out after {timeout} seconds"
    except Exception as e:
        logger.error(f"Compose execution exception: {e}")
        return False, str(e)


def compose_up(project_name: str, compose_dir: str, port: int, flag: str, build: bool = False):
    """
    Deploys container using docker compose up -d (with optional --build).
    """
    env_vars = {
        "PORT": port,
        "FLAG": flag,
    }
    cmd = ["up", "-d"]
    if build:
        cmd.append("--build")

    return run_compose_command(project_name, compose_dir, cmd, env_vars=env_vars, timeout=300)


def compose_down(project_name: str, compose_dir: str):
    """
    Destroys container using docker compose down -v.
    """
    return run_compose_command(project_name, compose_dir, ["down", "-v"], timeout=60)


def compose_restart(project_name: str, compose_dir: str, port: int = None, flag: str = None):
    """
    Restarts container using docker compose restart.
    """
    env_vars = {}
    if port:
        env_vars["PORT"] = port
    if flag:
        env_vars["FLAG"] = flag

    return run_compose_command(project_name, compose_dir, ["restart"], env_vars=env_vars, timeout=60)


def compose_rebuild(project_name: str, compose_dir: str, port: int, flag: str):
    """
    Rebuilds and restarts container using docker compose up -d --build.
    """
    return compose_up(project_name, compose_dir, port, flag, build=True)
