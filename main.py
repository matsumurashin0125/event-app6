# main.py
import os
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, timedelta
from models import db, Candidate, Confirmed, Attendance

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

    # ==========================
    #        ROUTES
    # ==========================

    @app.route("/", methods=["GET", "POST"])
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
    def confirm():
        candidates = Candidate.query.order_by(
            Candidate.year,
            Candidate.month,
            Candidate.day
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

    # ★ Render に必要：DB を自動作成（超重要）
    with app.app_context():
        db.create_all()

    return app


# ====== Render 起動 ======
app = create_app()

if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
