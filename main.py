import os
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta
from functools import wraps
from models import db, Candidate, Confirmed, Attendance


# ------------------------------
# 管理者ログイン保護
# ------------------------------
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated_function


def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")

    # ===== PostgreSQL必須 =====
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        raise RuntimeError("ERROR: DATABASE_URL が設定されていません。（PostgreSQL 専用版）")

    # Heroku形式 → SQLAlchemy形式へ変換
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "prod-key")

    db.init_app(app)

    # ============================================
    #             ADMIN LOGIN
    # ============================================
    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            password = request.form.get("password")
            if password == os.environ.get("ADMIN_PASSWORD", "admin123"):
                session["admin_logged_in"] = True
                return redirect(url_for("index"))
            return render_template("admin_login.html", error="パスワードが違います。")

        return render_template("admin_login.html")

    @app.route("/admin/logout")
    def admin_logout():
        session.pop("admin_logged_in", None)
        return redirect(url_for("admin_login"))

    # ============================================
    #                  ROUTES
    # ============================================
    @app.route("/", methods=["GET", "POST"])
    @admin_required
    def index():
        if request.method == "POST":
            cand = Candidate(
                year=int(request.form["year"]),
                month=int(request.form["month"]),
                day=int(request.form["day"]),
                gym=request.form.get("gym", ""),
                start=request.form.get("start", ""),
                end=request.form.get("end", "")
            )
            db.session.add(cand)
            db.session.commit()
            return redirect(url_for("confirm"))

        today = datetime.today()
        base = (today.replace(day=1) + timedelta(days=92)).replace(day=1)
        return render_template("index.html", base=base)

    @app.route("/confirm", methods=["GET", "POST"])
    @admin_required
    def confirm():
        candidates = Candidate.query.order_by(
            Candidate.year, Candidate.month, Candidate.day
        ).all()

        if request.method == "POST":
            c_id = int(request.form["candidate_id"])
            db.session.add(Confirmed(candidate_id=c_id))
            db.session.commit()
            return redirect(url_for("register"))

        return render_template("confirm.html", candidates=candidates)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        confirmed_list = (
            db.session.query(Confirmed, Candidate)
            .join(Candidate, Confirmed.candidate_id == Candidate.id)
            .order_by(Candidate.year, Candidate.month, Candidate.day)
            .all()
        )

        if request.method == "POST":
            event_id = int(request.form["event_id"])
            att = Attendance(
                event_id=event_id,
                name=request.form["name"],
                status=request.form["status"]
            )
            db.session.add(att)
            db.session.commit()
            return redirect(url_for("register", event_id=event_id))

        event_id = request.args.get("event_id")
        attendance = []
        if event_id:
            attendance = Attendance.query.filter_by(event_id=int(event_id)).all()

        return render_template(
            "register.html",
            events=confirmed_list,
            attendance=attendance,
            selected_event=event_id
        )

    # ====================================
    #      イベント編集（管理者のみ）
    # ====================================
    @app.route("/event/<int:event_id>/edit", methods=["GET", "POST"])
    @admin_required
    def edit_event(event_id):
        confirmed = Confirmed.query.get(event_id)
        if not confirmed:
            return "イベントが存在しません"

        cand = Candidate.query.get(confirmed.candidate_id)

        if request.method == "POST":
            cand.year = int(request.form["year"])
            cand.month = int(request.form["month"])
            cand.day = int(request.form["day"])
            cand.gym = request.form["gym"]
            cand.start = request.form["start"]
            cand.end = request.form["end"]

            db.session.commit()
            return redirect(url_for("register", event_id=event_id))

        return render_template("edit_event.html", event=cand, event_id=event_id)

    # ====================================
    #      イベント削除（管理者のみ）
    # ====================================
    @app.route("/event/<int:event_id>/delete", methods=["POST"])
    @admin_required
    def delete_event(event_id):
        confirmed = Confirmed.query.get(event_id)
        if not confirmed:
            return "イベントが存在しません"

        Attendance.query.filter_by(event_id=event_id).delete()
        db.session.delete(confirmed)
        db.session.commit()

        return redirect(url_for("register"))

    # ★ Render に必要：DB 自動作成
    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
