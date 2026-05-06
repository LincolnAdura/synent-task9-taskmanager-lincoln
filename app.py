# ============================================
# Synent Technologies - Python Internship
# Task 9: Full Stack Task Manager (Advanced)
# Developer: Lincoln Adura
# ============================================

from flask import Flask, render_template, redirect, url_for, request, flash # type: ignore
from flask_sqlalchemy import SQLAlchemy # type: ignore
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user # type: ignore
from werkzeug.security import generate_password_hash, check_password_hash # type: ignore
from datetime import datetime

app = Flask(__name__)
app.config["SECRET_KEY"] = "synent-lincoln-taskmanager-2024"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///taskmanager.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ============================================
# DATABASE MODELS
# ============================================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    tasks = db.relationship("Task", backref="user", lazy=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="Pending")
    priority = db.Column(db.String(20), default="Medium")
    due_date = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ============================================
# ROUTES
# ============================================

@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username").strip()
        email = request.form.get("email").strip()
        password = request.form.get("password").strip()

        if not username or not email or not password:
            flash("All fields are required!", "error")
            return redirect(url_for("register"))

        if User.query.filter_by(username=username).first():
            flash("Username already exists!", "error")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered!", "error")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email,
                        password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash("Account created successfully! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()

        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password, password):
            flash("Invalid username or password!", "error")
            return redirect(url_for("login"))

        login_user(user)
        flash(f"Welcome back, {user.username}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    status_filter = request.args.get("status", "All")
    priority_filter = request.args.get("priority", "All")

    tasks = Task.query.filter_by(user_id=current_user.id)

    if status_filter != "All":
        tasks = tasks.filter_by(status=status_filter)
    if priority_filter != "All":
        tasks = tasks.filter_by(priority=priority_filter)

    tasks = tasks.order_by(Task.created_at.desc()).all()

    total = Task.query.filter_by(user_id=current_user.id).count()
    pending = Task.query.filter_by(user_id=current_user.id,
                                   status="Pending").count()
    in_progress = Task.query.filter_by(user_id=current_user.id,
                                       status="In Progress").count()
    completed = Task.query.filter_by(user_id=current_user.id,
                                     status="Completed").count()

    return render_template("dashboard.html", tasks=tasks,
                           total=total, pending=pending,
                           in_progress=in_progress,
                           completed=completed,
                           status_filter=status_filter,
                           priority_filter=priority_filter)

@app.route("/add_task", methods=["GET", "POST"])
@login_required
def add_task():
    if request.method == "POST":
        title = request.form.get("title").strip()
        description = request.form.get("description").strip()
        status = request.form.get("status")
        priority = request.form.get("priority")
        due_date = request.form.get("due_date")

        if not title:
            flash("Task title is required!", "error")
            return redirect(url_for("add_task"))

        new_task = Task(title=title, description=description,
                        status=status, priority=priority,
                        due_date=due_date, user_id=current_user.id)
        db.session.add(new_task)
        db.session.commit()
        flash("Task added successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("add_task.html")

@app.route("/update_task/<int:task_id>", methods=["GET", "POST"])
@login_required
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash("Unauthorized access!", "error")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        task.title = request.form.get("title").strip()
        task.description = request.form.get("description").strip()
        task.status = request.form.get("status")
        task.priority = request.form.get("priority")
        task.due_date = request.form.get("due_date")
        db.session.commit()
        flash("Task updated successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("add_task.html", task=task)

@app.route("/delete_task/<int:task_id>")
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash("Unauthorized access!", "error")
        return redirect(url_for("dashboard"))
    db.session.delete(task)
    db.session.commit()
    flash("Task deleted successfully!", "success")
    return redirect(url_for("dashboard"))

# ============================================
# RUN APP
# ============================================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)