import os
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta, date
from functools import wraps
from models import db, Candidate, Confirmed, Attendance

app = Flask(__name__)
app.secret_key = "dummy_key_for_now"   # パスワード不要方式なので暫定的に固定キーを使う

# --------------------------------
# DB 初期化
# --------------------------------
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///data.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()


# --------------------------------
# 管理者ページ（パスワード不要）
# --------------------------------
@app.route("/admin")
def admin_menu():
    return render_template("admin_menu.html")


# --------------------------------
# 候補日入力
# --------------------------------
@app.route("/candidate", methods=["GET", "POST"])
def candidate():
    times = [f"{h}:00" for h in range(9, 22)]
    gyms = ["A体育館", "B体育館", "C体育館"]

    if request.method == "POST":
        year = int(request.form["year"])
        month = int(request.form["month"])
        day = int(request.form["day"])
        gym = request.form["gym"]
        start = request.form["start"]
        end = request.form["end"]

        cand = Candidate(year=year, month=month, day=day, gym=gym, start=start, end=end)
        db.session.add(cand)
        db.session.commit()

        return redirect(url_for("candidate"))

    candidates = Candidate.query.order_by(
        Candidate.year, Candidate.month, Candidate.day, Candidate.start
    ).all()

    return render_template("candidate.html", candidates=candidates, gyms=gyms, times=times)


# --------------------------------
# 候補日編集
# --------------------------------
@app.route("/candidate_edit/<int:id>", methods=["GET", "POST"])
def candidate_edit(id):
    cand = Candidate.query.get_or_404(id)
    times = [f"{h}:00" for h in range(9, 22)]
    gyms = ["A体育館", "B体育館", "C体育館"]

    if request.method == "POST":
        cand.year = int(request.form["year"])
        cand.month = int(request.form["month"])
        cand.day = int(request.form["day"])
        cand.gym = request.form["gym"]
        cand.start = request.form["start"]
        cand.end = request.form["end"]

        db.session.commit()
        return redirect(url_for("confirm"))

    return render_template("candidate_edit.html", cand=cand, gyms=gyms, times=times)


# --------------------------------
# 候補日削除
# --------------------------------
@app.route("/candidate_delete/<int:id>")
def candidate_delete(id):
    cand = Candidate.query.get_or_404(id)
    db.session.delete(cand)
    db.session.commit()
    return redirect(url_for("confirm"))


# --------------------------------
# 日程確定
# --------------------------------
@app.route("/confirm", methods=["GET", "POST"])
def confirm():
    candidates = Candidate.query.order_by(
        Candidate.year, Candidate.month, Candidate.day, Candidate.start
    ).all()

    confirmed = Confirmed.query.first()

    if request.method == "POST":
        selected = int(request.form["selected"])
        confirmed = Confirmed.query.first()

        if confirmed:
            confirmed.candidate_id = selected
        else:
            confirmed = Confirmed(candidate_id=selected)
            db.session.add(confirmed)

        db.session.commit()
        return redirect(url_for("confirm"))

    return render_template("confirm.html", candidates=candidates, confirmed=confirmed)


# --------------------------------
# 参加登録
# --------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    users = ["松村", "山火", "山根", "奥迫", "川崎"]

    confirmed = Confirmed.query.first()
    if not confirmed:
        return render_template("register_wait.html")

    event = Candidate.query.get(confirmed.candidate_id)

    if request.method == "POST":
        name = request.form["name"]
        status = request.form["status"]

        existing = Attendance.query.filter_by(name=name).first()

        if existing:
            existing.status = status
        else:
            db.session.add(Attendance(name=name, status=status, event_id=event.id))

        db.session.commit()
        return redirect(url_for("register"))

    attendance = Attendance.query.all()

    return render_template("register.html", users=users, event=event, attendance=attendance)


# --------------------------------
# 新規追加：参加一覧ページ（方法B）
# --------------------------------
@app.route("/attendance_list")
def attendance_list():

    """
    Attendance  ---event_id--->  Confirmed  ---candidate_id--->  Candidate
    """

    records = (
        db.session.query(Attendance, Candidate)
        .join(Candidate, Attendance.event_id == Candidate.id)
        .all()
    )

    return render_template("attendance_list.html", records=records)


# --------------------------------
# ホーム
# --------------------------------
@app.route("/")
def home():
    return render_template("home.html")


if __name__ == "__main__":
    app.run(debug=True)
