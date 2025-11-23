import os
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta, date
from functools import wraps
from models import db, Candidate, Confirmed, Attendance


# ------------------------------
# 管理者ログイン保護
# ------------------------------
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("admin_logged_in") != True:
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated_function


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

    # DB 初期化
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///event.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()

    # ------------------------------
    # 管理者ログイン
    # ------------------------------
    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        error = None
        if request.method == "POST":
            user = request.form.get("username")
            pw = request.form.get("password")

            if user == os.environ.get("ADMIN_USER", "admin") and pw == os.environ.get("ADMIN_PASSWORD", "password"):
                session["admin_logged_in"] = True
                return redirect(url_for("confirm"))
            else:
                error = "ログイン情報が違います。"
        return render_template("admin_login.html", error=error)

    @app.route("/admin/logout")
    def admin_logout():
        session.pop("admin_logged_in", None)
        return redirect(url_for("admin_login"))

    # ------------------------------
    # 候補日入力
    # ------------------------------
    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "POST":
            date_str = request.form.get("date")
            time_str = request.form.get("time")
            memo = request.form.get("memo")

            if date_str and time_str:
                dt = datetime.strptime(date_str + " " + time_str, "%Y-%m-%d %H:%M")
                candidate = Candidate(date_time=dt, memo=memo)
                db.session.add(candidate)
                db.session.commit()
            return redirect(url_for("index"))

        candidates = Candidate.query.order_by(Candidate.date_time.asc()).all()
        return render_template("index.html", candidates=candidates)

    # ------------------------------
    # 日程確定（管理者）
    # ------------------------------
    @app.route("/confirm", methods=["GET", "POST"])
    @admin_required
    def confirm():
        if request.method == "POST":
            candidate_id = request.form.get("candidate_id")
            candidate = Candidate.query.get(candidate_id)

            if candidate:
                Confirmed.query.delete()
                confirmed = Confirmed(date_time=candidate.date_time, memo=candidate.memo)
                db.session.add(confirmed)
                db.session.commit()

        candidates = Candidate.query.order_by(Candidate.date_time.asc()).all()
        confirmed = Confirmed.query.first()
        return render_template("confirm.html", candidates=candidates, confirmed=confirmed)

    # ------------------------------
    # 参加登録
    # ------------------------------
    @app.route("/register", methods=["GET", "POST"])
    def register():
        confirmed = Confirmed.query.first()

        if request.method == "POST":
            name = request.form.get("name")
            status = request.form.get("status")
            memo = request.form.get("memo")

            if confirmed and name and status:
                attendance = Attendance(name=name, status=status, memo=memo)
                db.session.add(attendance)
                db.session.commit()

            return redirect(url_for("register"))

        attendance_list = Attendance.query.all()
        return render_template("register.html", confirmed=confirmed, attendance_list=attendance_list)

    # =====================================================================
    # 編集・削除（インデント正常化済み・全角空白なし）
    # =====================================================================

    # ------------------------------
    # 候補日：編集
    # ------------------------------
    @app.route("/candidate/<int:id>/edit", methods=["GET", "POST"])
    @admin_required
    def edit_candidate(id):
        candidate = Candidate.query.get_or_404(id)

        if request.method == "POST":
            date_str = request.form.get("date")
            time_str = request.form.get("time")
            memo = request.form.get("memo")

            candidate.date_time = datetime.strptime(date_str + " " + time_str, "%Y-%m-%d %H:%M")
            candidate.memo = memo

            db.session.commit()
            return redirect(url_for("confirm"))

        return render_template("edit_candidate.html", candidate=candidate)

    # ------------------------------
    # 候補日：削除
    # ------------------------------
    @app.route("/candidate/<int:id>/delete", methods=["POST"])
    @admin_required
    def delete_candidate(id):
        candidate = Candidate.query.get_or_404(id)
        db.session.delete(candidate)
        db.session.commit()
        return redirect(url_for("confirm"))

    # ------------------------------
    # 参加登録：編集
    # ------------------------------
    @app.route("/attendance/<int:id>/edit", methods=["GET", "POST"])
    @admin_required
    def edit_attendance(id):
        attendance = Attendance.query.get_or_404(id)

        if request.method == "POST":
            attendance.name = request.form.get("name")
            attendance.status = request.form.get("status")
            attendance.memo = request.form.get("memo")
            db.session.commit()
            return redirect(url_for("register"))

        return render_template("edit_attendance.html", attendance=attendance)

    # ------------------------------
    # 参加登録：削除
    # ------------------------------
    @app.route("/attendance/<int:id>/delete", methods=["POST"])
    @admin_required
    def delete_attendance(id):
        attendance = Attendance.query.get_or_404(id)
        db.session.delete(attendance)
        db.session.commit()
        return redirect(url_for("register"))

    return app
