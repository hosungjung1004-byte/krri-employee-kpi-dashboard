"""KRRI 직원 KPI 관리 대시보드 (Flask + SQLite)."""

from __future__ import annotations

import csv
import io
import os
import secrets
import sqlite3
import threading
import webbrowser
from datetime import date
from pathlib import Path

from flask import Flask, Response, flash, jsonify, redirect, render_template, request, url_for


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "kpi.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))

DEPARTMENTS = ["미래교통연구본부", "철도안전연구본부", "스마트전기신호본부", "교통환경연구본부", "경영지원본부"]
QUARTERS = ["2026 Q1", "2026 Q2", "2026 Q3", "2026 Q4"]


def db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_no TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                position TEXT NOT NULL,
                email TEXT DEFAULT '',
                joined_at TEXT DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS kpis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                quarter TEXT NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                target REAL NOT NULL,
                actual REAL NOT NULL DEFAULT 0,
                unit TEXT DEFAULT '',
                weight REAL NOT NULL DEFAULT 25,
                note TEXT DEFAULT '',
                updated_at TEXT NOT NULL,
                FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );
            """
        )
        if conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 0:
            employees = [
                ("K26001", "이정우", "미래교통연구본부", "책임연구원", "jwlee@krri.re.kr", "2015-03-02"),
                ("K26002", "박서연", "스마트전기신호본부", "선임연구원", "sypark@krri.re.kr", "2018-07-16"),
                ("K26003", "최민석", "미래교통연구본부", "수석연구원", "mschoi@krri.re.kr", "2012-01-09"),
                ("K26004", "한지훈", "교통환경연구본부", "선임연구원", "jhhan@krri.re.kr", "2019-05-20"),
                ("K26005", "윤하늘", "스마트전기신호본부", "책임연구원", "hnyoon@krri.re.kr", "2016-09-01"),
                ("K26006", "김태윤", "철도안전연구본부", "책임연구원", "tykim@krri.re.kr", "2014-02-17"),
                ("K26007", "서은지", "교통환경연구본부", "연구원", "ejseo@krri.re.kr", "2022-11-07"),
                ("K26008", "오세진", "경영지원본부", "선임행정원", "sjo@krri.re.kr", "2017-04-03"),
            ]
            conn.executemany("INSERT INTO employees(employee_no,name,department,position,email,joined_at) VALUES(?,?,?,?,?,?)", employees)
            ids = [row[0] for row in conn.execute("SELECT id FROM employees ORDER BY id")]
            scores = [(10, 9, 4, 3), (8, 7, 3, 2.8), (12, 12, 5, 5), (9, 6.2, 4, 2.9), (10, 8.7, 4, 3.7), (8, 6.5, 3, 2.6), (7, 6.7, 3, 2.8), (10, 7.8, 4, 3.5)]
            rows = []
            for employee_id, values in zip(ids, scores):
                rows.extend([
                    (employee_id, "2026 Q3", "연구성과", "핵심 연구 마일스톤 달성", values[0], values[1], "건", 45, "", str(date.today())),
                    (employee_id, "2026 Q3", "논문·특허", "SCI 논문 및 특허 성과", values[2], values[3], "건", 30, "", str(date.today())),
                    (employee_id, "2026 Q3", "조직기여", "협업 및 조직 기여도", 100, 78 + employee_id * 2, "점", 25, "", str(date.today())),
                ])
            conn.executemany("INSERT INTO kpis(employee_id,quarter,category,title,target,actual,unit,weight,note,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)", rows)


def score_for(kpis: list[dict] | list[sqlite3.Row]) -> float:
    if not kpis:
        return 0.0
    weight_sum = sum(float(k["weight"]) for k in kpis)
    if weight_sum <= 0:
        return 0.0
    weighted = sum(min(float(k["actual"]) / float(k["target"]) * 100, 120) * float(k["weight"]) for k in kpis if float(k["target"]) > 0)
    return round(weighted / weight_sum, 1)


def status_for(score: float) -> str:
    if score >= 100:
        return "탁월"
    if score >= 85:
        return "양호"
    if score >= 70:
        return "주의"
    return "개선필요"


def get_dashboard_rows(quarter: str) -> list[dict]:
    with db() as conn:
        employees = conn.execute("SELECT * FROM employees WHERE active=1 ORDER BY department,name").fetchall()
        result = []
        for employee in employees:
            kpis = conn.execute("SELECT * FROM kpis WHERE employee_id=? AND quarter=? ORDER BY id", (employee["id"], quarter)).fetchall()
            score = score_for(kpis)
            item = dict(employee)
            item.update(score=score, status=status_for(score), kpi_count=len(kpis), completed=sum(1 for k in kpis if k["actual"] >= k["target"]))
            result.append(item)
        return result


@app.route("/")
def dashboard():
    quarter = request.args.get("quarter", "2026 Q3")
    department = request.args.get("department", "전체")
    status = request.args.get("status", "전체")
    query = request.args.get("q", "").strip().lower()
    rows = get_dashboard_rows(quarter)
    all_rows = rows.copy()
    if department != "전체":
        rows = [x for x in rows if x["department"] == department]
    if status != "전체":
        rows = [x for x in rows if x["status"] == status]
    if query:
        rows = [x for x in rows if query in f"{x['name']} {x['employee_no']} {x['position']}".lower()]
    scores = [x["score"] for x in all_rows]
    summary = {
        "employees": len(all_rows),
        "average": round(sum(scores) / len(scores), 1) if scores else 0,
        "excellent": sum(1 for x in all_rows if x["status"] == "탁월"),
        "attention": sum(1 for x in all_rows if x["status"] in ("주의", "개선필요")),
        "completion": round(sum(x["completed"] for x in all_rows) / max(sum(x["kpi_count"] for x in all_rows), 1) * 100, 1),
    }
    distribution = {name: sum(1 for x in all_rows if x["status"] == name) for name in ["탁월", "양호", "주의", "개선필요"]}
    dept_scores = []
    for dept in DEPARTMENTS:
        values = [x["score"] for x in all_rows if x["department"] == dept]
        if values:
            dept_scores.append({"name": dept.replace("연구본부", "").replace("본부", ""), "score": round(sum(values) / len(values), 1)})
    return render_template("index.html", rows=rows, all_rows=all_rows, summary=summary, distribution=distribution, dept_scores=dept_scores, departments=DEPARTMENTS, quarters=QUARTERS, filters={"quarter": quarter, "department": department, "status": status, "q": request.args.get("q", "")})


@app.get("/api/employees/<int:employee_id>")
def employee_detail(employee_id: int):
    quarter = request.args.get("quarter", "2026 Q3")
    with db() as conn:
        employee = conn.execute("SELECT * FROM employees WHERE id=?", (employee_id,)).fetchone()
        if not employee:
            return jsonify({"error": "직원을 찾을 수 없습니다."}), 404
        kpis = [dict(x) for x in conn.execute("SELECT * FROM kpis WHERE employee_id=? AND quarter=? ORDER BY id", (employee_id, quarter)).fetchall()]
    score = score_for(kpis)
    return jsonify({"employee": dict(employee), "kpis": kpis, "score": score, "status": status_for(score)})


@app.post("/employees")
def add_employee():
    values = [request.form.get(name, "").strip() for name in ["employee_no", "name", "department", "position", "email", "joined_at"]]
    if not all(values[:4]):
        flash("사번, 이름, 부서와 직급은 필수입니다.", "error")
        return redirect(url_for("dashboard"))
    try:
        with db() as conn:
            conn.execute("INSERT INTO employees(employee_no,name,department,position,email,joined_at) VALUES(?,?,?,?,?,?)", values)
        flash(f"{values[1]} 직원을 등록했습니다.", "success")
    except sqlite3.IntegrityError:
        flash("이미 등록된 사번입니다.", "error")
    return redirect(url_for("dashboard"))


@app.post("/employees/<int:employee_id>/edit")
def edit_employee(employee_id: int):
    values = [request.form.get(name, "").strip() for name in ["employee_no", "name", "department", "position", "email", "joined_at"]]
    with db() as conn:
        conn.execute("UPDATE employees SET employee_no=?,name=?,department=?,position=?,email=?,joined_at=? WHERE id=?", (*values, employee_id))
    flash("직원 정보를 수정했습니다.", "success")
    return redirect(request.referrer or url_for("dashboard"))


@app.post("/employees/<int:employee_id>/archive")
def archive_employee(employee_id: int):
    with db() as conn:
        conn.execute("UPDATE employees SET active=0 WHERE id=?", (employee_id,))
    flash("직원을 보관 처리했습니다.", "success")
    return redirect(url_for("dashboard"))


@app.post("/kpis")
def add_kpi():
    employee_id = request.form.get("employee_id", type=int)
    try:
        target = float(request.form.get("target", 0))
        actual = float(request.form.get("actual", 0))
        weight = float(request.form.get("weight", 0))
    except ValueError:
        flash("목표·실적·가중치는 숫자로 입력하세요.", "error")
        return redirect(url_for("dashboard"))
    if not employee_id or target <= 0 or weight <= 0:
        flash("직원, 목표와 가중치를 올바르게 입력하세요.", "error")
        return redirect(url_for("dashboard"))
    with db() as conn:
        conn.execute(
            "INSERT INTO kpis(employee_id,quarter,category,title,target,actual,unit,weight,note,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (employee_id, request.form["quarter"], request.form["category"], request.form["title"].strip(), target, actual, request.form.get("unit", ""), weight, request.form.get("note", ""), str(date.today())),
        )
    flash("KPI 항목을 등록했습니다.", "success")
    return redirect(url_for("dashboard", quarter=request.form["quarter"]))


@app.post("/kpis/<int:kpi_id>/update")
def update_kpi(kpi_id: int):
    actual = request.form.get("actual", type=float)
    if actual is None:
        return jsonify({"error": "올바른 실적을 입력하세요."}), 400
    with db() as conn:
        conn.execute("UPDATE kpis SET actual=?, updated_at=? WHERE id=?", (actual, str(date.today()), kpi_id))
    return jsonify({"ok": True})


@app.get("/export.csv")
def export_csv():
    quarter = request.args.get("quarter", "2026 Q3")
    rows = get_dashboard_rows(quarter)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["사번", "성명", "부서", "직급", "KPI 수", "완료 수", "종합점수", "상태", "평가기간"])
    for row in rows:
        writer.writerow([row["employee_no"], row["name"], row["department"], row["position"], row["kpi_count"], row["completed"], row["score"], row["status"], quarter])
    return Response("\ufeff" + output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename=KRRI_KPI_{quarter.replace(' ', '_')}.csv"})


@app.get("/health")
def health():
    return {"status": "ok", "app": "KRRI KPI Dashboard"}


init_db()

if __name__ == "__main__":
    threading.Timer(1.2, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
