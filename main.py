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

    # DB 設定
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL が設定されていません")

    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "prod-key")

    db.init_app(app)

    # ------------------------------
    # 管理者ログイン
    # ------------------------------
    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            password = request.form.get("password")
            if password == os.environ.get("ADMIN_PASSWORD", "admin123"):
                session["admin_logged_in"] = True
                return redirect(url_for("admin_menu"))
            return render_template("admin_login.html", error="パスワードが違います。")

        return render_template("admin_login.html")

    @app.route("/admin/logout")
    def admin_logout():
        session.pop("admin_logged_in", None)
        return redirect(url_for("home"))

    # ------------------------------
    # トップページ
    # ------------------------------
    @app.route("/")
    @app.route("/home")
    def home():
        return render_template("home.html")

    # ------------------------------
    # 管理者メニュー
    # ------------------------------
    @app.route("/admin")
    @admin_required
    def admin_menu():
        return render_template("admin_menu.html")

    # ------------------------------
    # 候補日追加
    # ------------------------------
    @app.route("/candidate", methods=["GET", "POST"])
    @admin_required
    def candidate():
        gyms = ["中平井", "平井", "西小岩", "北小岩", "南小岩"]

        # 時刻（18:00 〜 22:00 30分刻み）
        times = []
        for h in range(18, 23):
            times.append(f"{h:02d}:00")
            times.append(f"{h:02d}:30")
        times = times[:-1]  # 22:30 不要

        today = datetime.today()
        base = (today.replace(day=1) + timedelta(days=92)).replace(day=1)

        years = [base.year, base.year + 1]
        months = list(range(1, 13))
        days = list(range(1, 32))

        if request.method == "POST":
            year = int(request.form["year"])
            month = int(request.form["month"])
            day = int(request.form["day"])

            cand = Candidate(
                year=year,
                month=month,
                day=day,
                gym=request.form["gym"],
                start=request.form["start"],
                end=request.form["end"]
            )
            db.session.add(cand)
            db.session.commit()

            return render_template(
                "candidate.html",
                years=years, months=months, days=days,
                gyms=gyms, times=times,
                selected_year=year,
                selected_month=month,
                selected_day=day,
                selected_gym=request.form["gym"],
                selected_start=request.form["start"],
                selected_end=request.form["end"]
            )

        return render_template(
            "candidate.html",
            years=years, months=months, days=days,
            gyms=gyms, times=times,
            selected_year=base.year,
            selected_month=base.month,
            selected_day=base.day,
            selected_gym="中平井",
            selected_start="18:00",
            selected_end="19:00"
        )

    # ------------------------------
    # 候補日確認・確定 （編集・削除つき）
    # ------------------------------
    @app.route("/confirm", methods=["GET", "POST"])
    @admin_required
    def confirm():
        candidates = Candidate.query.order_by(
            Candidate.year, Candidate.month, Candidate.day
        ).all()

        if request.method == "POST":
            cid = int(request.form["candidate_id"])
            exists = Confirmed.query.filter_by(candidate_id=cid).first()
            if not exists:
                db.session.add(Confirmed(candidate_id=cid))
                db.session.commit()
            return redirect(url_for("confirm"))

        confirmed = (
            db.session.query(Confirmed, Candidate)
            .join(Candidate, Confirmed.candidate_id == Candidate.id)
            .order_by(Candidate.year, Candidate.month, Candidate.day)
            .all()
        )

        return render_template(
            "confirm.html",
            candidates=candidates,
            confirmed=confirmed
        )

    # ------------------------------
    # イベント編集（候補日も確定日も同じ画面）
    # ------------------------------
    @app.route("/event/<int:candidate_id>/edit", methods=["GET", "POST"])
    @admin_required
    def edit_event(candidate_id):
        cand = Candidate.query.get(candidate_id)
        if not cand:
            return "候補日が存在しません"

        gyms = ["中平井", "平井", "西小岩", "北小岩", "南小岩"]

        times = []
        for h in range(18, 23):
            times.append(f"{h:02d}:00")
            times.append(f"{h:02d}:30")
        times = times[:-1]

        years = [cand.year, cand.year + 1]
        months = list(range(1, 13))
        days = list(range(1, 32))

        if request.method == "POST":
            cand.year = int(request.form["year"])
            cand.month = int(request.form["month"])
            cand.day = int(request.form["day"])
            cand.gym = request.form["gym"]
            cand.start = request.form["start"]
            cand.end = request.form["end"]

            db.session.commit()

            return redirect(url_for("confirm"))

        return render_template(
            "edit_event.html",
            cand=cand,
            years=years, months=months, days=days,
            gyms=gyms, times=times
        )

    # ------------------------------
    # イベント削除（候補でも確定でも削除可）
    # ------------------------------
    @app.route("/event/<int:candidate_id>/delete", methods=["POST"])
    @admin_required
    def delete_event(candidate_id):
        # → 確定済みなら Confirmed と Attendance を削除
        confirmed = Confirmed.query.filter_by(candidate_id=candidate_id).first()
        if confirmed:
            Attendance.query.filter_by(event_id=confirmed.id).delete()
            db.session.delete(confirmed)

        # → 候補日自体削除
        cand = Candidate.query.get(candidate_id)
        if cand:
            db.session.delete(cand)

        db.session.commit()
        return redirect(url_for("confirm"))

    # ------------------------------
    # 出欠登録（管理者でも一般でも）
    # ------------------------------
    @app.route("/register", methods=["GET", "POST"])
    def register():
        confirmed_list = (
            db.session.query(Confirmed, Candidate)
            .join(Candidate, Confirmed.candidate_id == Candidate.id)
            .order_by(Candidate.year, Candidate.month, Candidate.day)
            .all()
        )

        member_list = ["松村", "山火", "山根", "奥迫", "川崎"]

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
        attendance = Attendance.query.filter_by(event_id=event_id).all() if event_id else []

        return render_template(
            "register.html",
            events=confirmed_list,
            attendance=attendance,
            selected_event=event_id,
            members=member_list
        )

    with app.app_context():
        db.create_all()

    return app


app = create_app()
