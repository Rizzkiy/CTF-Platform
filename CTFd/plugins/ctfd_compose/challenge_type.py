from flask import Blueprint
from CTFd.exceptions.challenges import (
    ChallengeCreateException,
    ChallengeUpdateException,
)
from CTFd.models import (
    ChallengeFiles,
    Challenges,
    Fails,
    Flags,
    Hints,
    Partials,
    Ratelimiteds,
    SolutionFiles,
    Solutions,
    SolutionUnlocks,
    Solves,
    Tags,
    db,
)
from CTFd.plugins.challenges import BaseChallenge
from CTFd.plugins.flags import get_flag_class
from CTFd.utils.user import get_current_user
from CTFd.plugins.ctfd_compose.models import ComposeChallenge, ComposeContainer
from CTFd.plugins.ctfd_compose.utils.docker_compose import compose_down


class ComposeChallengeType(BaseChallenge):
    id = "compose"
    name = "compose"
    templates = {
        "create": "/plugins/ctfd_compose/assets/create.html",
        "update": "/plugins/ctfd_compose/assets/update.html",
        "view": "/plugins/ctfd_compose/assets/view.html",
    }
    scripts = {
        "create": "/plugins/ctfd_compose/assets/create.js",
        "update": "/plugins/ctfd_compose/assets/update.js",
        "view": "/plugins/ctfd_compose/assets/view.js",
    }
    route = "/plugins/ctfd_compose/assets/"
    blueprint = Blueprint(
        "ctfd_compose",
        __name__,
        template_folder="templates",
        static_folder="assets",
    )
    challenge_model = ComposeChallenge

    @classmethod
    def create(cls, request):
        data = dict(request.form or request.get_json() or {})
        
        # Handle dynamic_flag boolean checkbox
        dynamic_flag = data.get("dynamic_flag")
        if dynamic_flag in ("1", "true", "True", True, 1, "on"):
            data["dynamic_flag"] = True
        else:
            data["dynamic_flag"] = False

        if "timeout" in data:
            data["timeout"] = int(data["timeout"])
        if "max_renew" in data:
            data["max_renew"] = int(data["max_renew"])
        if "service_port" in data:
            data["service_port"] = int(data["service_port"])

        challenge = cls.challenge_model(**data)
        db.session.add(challenge)
        db.session.commit()
        return challenge

    @classmethod
    def read(cls, challenge):
        data = {
            "id": challenge.id,
            "name": challenge.name,
            "value": challenge.value,
            "description": challenge.description,
            "connection_info": challenge.connection_info,
            "next_id": challenge.next_id,
            "category": challenge.category,
            "state": challenge.state,
            "max_attempts": challenge.max_attempts,
            "type": challenge.type,
            "type_data": {
                "id": cls.id,
                "name": cls.name,
                "templates": cls.templates,
                "scripts": cls.scripts,
            },
            "compose_dir": challenge.compose_dir,
            "service_port": challenge.service_port,
            "redirect_type": challenge.redirect_type,
            "timeout": challenge.timeout,
            "max_renew": challenge.max_renew,
            "dynamic_flag": challenge.dynamic_flag,
            "flag_template": challenge.flag_template,
        }
        return data

    @classmethod
    def update(cls, challenge, request):
        data = dict(request.form or request.get_json() or {})

        if "dynamic_flag" in data:
            val = data.get("dynamic_flag")
            data["dynamic_flag"] = val in ("1", "true", "True", True, 1, "on")

        if "timeout" in data and data["timeout"]:
            data["timeout"] = int(data["timeout"])
        if "max_renew" in data and data["max_renew"]:
            data["max_renew"] = int(data["max_renew"])
        if "service_port" in data and data["service_port"]:
            data["service_port"] = int(data["service_port"])

        for attr, value in data.items():
            setattr(challenge, attr, value)

        db.session.commit()
        return challenge

    @classmethod
    def delete(cls, challenge):
        # Stop and clean up any containers running for this challenge
        containers = ComposeContainer.query.filter_by(challenge_id=challenge.id).all()
        for c in containers:
            try:
                compose_down(c.project_name, c.compose_dir)
            except Exception:
                pass
            db.session.delete(c)

        Fails.query.filter_by(challenge_id=challenge.id).delete()
        Solves.query.filter_by(challenge_id=challenge.id).delete()
        Flags.query.filter_by(challenge_id=challenge.id).delete()
        files = ChallengeFiles.query.filter_by(challenge_id=challenge.id).all()
        for f in files:
            from CTFd.utils.uploads import delete_file
            delete_file(f.id)
        ChallengeFiles.query.filter_by(challenge_id=challenge.id).delete()
        Tags.query.filter_by(challenge_id=challenge.id).delete()
        Hints.query.filter_by(challenge_id=challenge.id).delete()
        solution = Solutions.query.filter_by(challenge_id=challenge.id).first()
        if solution:
            solution_files = SolutionFiles.query.filter_by(
                solution_id=solution.id
            ).all()
            for f in solution_files:
                from CTFd.utils.uploads import delete_file
                delete_file(f.id)
            SolutionUnlocks.query.filter_by(target=solution.id).delete()
            Solutions.query.filter_by(id=solution.id).delete()
        
        cls.challenge_model.query.filter_by(id=challenge.id).delete()
        Challenges.query.filter_by(id=challenge.id).delete()
        db.session.commit()

    @classmethod
    def attempt(cls, challenge, request):
        data = request.form or request.get_json()
        submission = data["submission"].strip()
        user = get_current_user()

        if not user:
            return False, "You must be logged in to submit a flag"

        # Check dynamic flag first if enabled
        if challenge.dynamic_flag:
            container = ComposeContainer.query.filter_by(
                user_id=user.id,
                challenge_id=challenge.id,
                status="running",
            ).first()

            if container and container.flag and submission == container.flag.strip():
                return True, "Correct"

        # Fallback to standard static flags in Flags table
        flags = Flags.query.filter_by(challenge_id=challenge.id).all()
        for flag in flags:
            if get_flag_class(flag.type).compare(flag, submission):
                return True, "Correct"

        return False, "Incorrect"
