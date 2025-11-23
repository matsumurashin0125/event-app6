import os
import calendar
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta, date
from functools import wraps
from models import db, Candidate, Confirmed, Attendance

app = Flask(__name__)
app.secret_key = "dummy_key_for_now"

# --------------------------------
# DB 初期化
# --------------------------------
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///data.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()


# --------------------------------
# 管理者メニュー（パスワードなし）
# --------------------------------
@app.route("/admin")
def admin_menu():
    return render_template("admin_menu.html")


# --------------------------------
# 候補日入力
# --------------------------------
@app.route("/candidate", methods=["GET", "POST"])
def candidate():

    # ----- デフォルト日付（現在から3ヶ月後の1日） -----
    today = date.today()
    month_offset = today.month + 3
    default_year = today.year + (month_offset - 1) // 12
    default_month = (month_offset - 1) % 12 + 1
    default_day = 1

    # 年・月・日リスト
    years = [default_year - 1, default_year, default_year + 1]
    months = list(range(1, 12 + 1))

    # 日 + 曜日
    month_range = calendar.monthrange(default_year, default_month)[1]
    days = []
    for d in range(1, month_range + 1):
        w = ["月", "火", "水", "木", "金", "土", "日"][date(default_year, default_month, d).weekday()]
        days.append({"day": d, "label": f"{d} ({w})"})

    # 体育館
    gyms = ["中平井", "平井", "西小岩", "北小岩", "南小岩"]

    # 30分刻み時間
    times = []
    for h in range(9, 23):
        times.append(f"{h:02}:00")
        times.append(f"{h:02}:30")

    # デフォルト選択
    selected_year = default_year
    selected_month = default_month
    selected_day = default_day
    selected_gym = "中平井"
    selected_start = "18:00"
    selected_end = "19:00"

    # POST 処理
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

    return render_template(
        "candidate.html",
        years=years,
        months=months,
        days=days,
        gyms=gyms,
        times=times,
        selected_year=selected_year,
        selected_month=selected_month,
        selected_day=selected_day,
        selected_gym=selected_gym,
        selected_start=selected_start,
        selected_end=selected_end
    )


# --------------------------------
# 候補日編集
# --------------------------------
@app.route("/candidate_edit/<int:id>", methods=["GET", "POST"])
def candidate_edit(id):
    cand = Candidate.query.get_or_404(id)

    # 体育館
    gyms = ["中平井", "平井", "西小岩", "北小岩", "南小岩"]

    # 30分刻み時間
    times = []
    for h in range(9, 23):
        times.append(f"{h:02}:00")
        times.append(f"{h:02}:30")

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
# 参加一覧ページ
# --------------------------------
@app.route("/attendance_list")
def attendance_list():

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
