from datetime import datetime
from CTFd.models import db, Challenges


class ComposeChallenge(Challenges):
    __mapper_args__ = {"polymorphic_identity": "compose"}
    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    compose_dir = db.Column(db.String(255), default="")
    service_port = db.Column(db.Integer, default=80)
    redirect_type = db.Column(db.String(32), default="http")  # 'http' or 'direct'
    timeout = db.Column(db.Integer, default=1200)  # seconds (20 mins)
    max_renew = db.Column(db.Integer, default=3)
    dynamic_flag = db.Column(db.Boolean, default=True)
    flag_template = db.Column(db.String(255), default="CTF{compose_{token}}")

    def __init__(self, *args, **kwargs):
        super(ComposeChallenge, self).__init__(**kwargs)
        self.value = kwargs.get("value", 100)


class ComposeContainer(db.Model):
    __tablename__ = "compose_containers"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    challenge_id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), index=True
    )
    project_name = db.Column(db.String(128), unique=True, index=True)
    compose_dir = db.Column(db.String(255))
    port = db.Column(db.Integer)
    flag = db.Column(db.String(255))
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, index=True)
    renew_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(32), default="running")

    def __repr__(self):
        return f"<ComposeContainer {self.project_name} port={self.port} user={self.user_id}>"
