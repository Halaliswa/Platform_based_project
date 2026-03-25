import os
import secrets
import string
import qrcode
from io import BytesIO
from flask import send_file
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash



 models import db, User, Workshop, Registration, Attendance, Feedback, Notification
from forms import RegisterForm, LoginForm, WorkshopForm, FeedbackForm, FacilitatorForm

app = Flask(__name__)

# --- CONFIGURATION ---
app.config["SECRET_KEY"] = "pbdv-group-23-innovation-key-2024"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///peer_workshop.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Use environment variables for security
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False
app.config["MAIL_USERNAME"] = "halaliswantshembeni@gmail.com"
app.config["MAIL_PASSWORD"] = "gnfueegfxzwfmsbc"
app.config["MAIL_DEFAULT_SENDER"] = "halaliswantshembeni@gmail.com"

# Default admin
DEFAULT_ADMIN_EMAIL = "dutpeerhub@dut.ac.za"
DEFAULT_ADMIN_PASSWORD = "Admin@123"

# --- INITIALIZATION ---
db.init_app(app)
mail = Mail(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------- HELPERS ----------
def generate_temp_password(length=10):
    chars = string.ascii_letters + string.digits + "@#$!"
    return "".join(secrets.choice(chars) for _ in range(length))


def seed_default_admin():
    admin = User.query.filter_by(email=DEFAULT_ADMIN_EMAIL).first()
    if not admin:
        admin = User(
            full_name="System Admin",
            email=DEFAULT_ADMIN_EMAIL,
            password=generate_password_hash(DEFAULT_ADMIN_PASSWORD),
            role="admin",
            popia_consent=True,
            consent_date=datetime.utcnow(),
            is_suspended=False
        )
        db.session.add(admin)
        db.session.commit()
        print("Default admin created.")


# Initialize Database Structure
with app.app_context():
    db.create_all()
    seed_default_admin()


# --- 1. HOME & FILTERING ---
@app.route("/")
def index():
    category = request.args.get("category")
    level = request.args.get("level")
    faculty = request.args.get("faculty")

    query = Workshop.query
    if category:
        query = query.filter_by(category=category)
    if level:
        query = query.filter_by(level=level)
    if faculty and faculty != "":
        query = query.filter_by(faculty=faculty)

    workshops = query.order_by(Workshop.date.asc()).all()
    return render_template("index.html", workshops=workshops)


# --- 2. AUTHENTICATION ---
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    form = RegisterForm()

    if form.validate_on_submit():
        email = form.email.data.strip().lower()

        if User.query.filter_by(email=email).first():
            flash("This email is already registered.", "danger")
            return redirect(url_for("register"))

        # Only students can self-register
        user = User(
            full_name=form.full_name.data.strip(),
            email=email,
            password=generate_password_hash(form.password.data),
            role="student",
            popia_consent=form.popia_consent.data,
            consent_date=datetime.utcnow(),
            is_suspended=False
        )

        try:
            db.session.add(user)
            db.session.commit()
            flash("Student account created successfully. Please login.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            db.session.rollback()
            flash(f"Database error: {str(e)}", "danger")

    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, form.password.data):
            if getattr(user, "is_suspended", False):
                flash("Your account has been suspended. Please contact the administrator.", "danger")
                return redirect(url_for("login"))

            login_user(user)
            flash("Login successful.", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "info")
    return redirect(url_for("index"))


# --- 3. DASHBOARDS ---
@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == "admin":
        faculty_filter = request.args.get("faculty")

        total_workshops = Workshop.query.count()
        total_students = User.query.filter_by(role="student").count()
        total_facilitators = User.query.filter_by(role="facilitator").count()
        total_registrations = Registration.query.count()
        total_feedback = Feedback.query.count()

        query = Workshop.query

        if faculty_filter and faculty_filter != "":
            query = query.filter_by(faculty=faculty_filter)

        workshops = query.order_by(Workshop.date.asc()).all()
        facilitators = User.query.filter_by(role="facilitator").order_by(User.full_name.asc()).all()

        return render_template(
            "admin_dashboard.html",
            workshops=workshops,
            facilitators=facilitators,
            total_workshops=total_workshops,
            total_students=total_students,
            total_facilitators=total_facilitators,
            total_registrations=total_registrations,
            total_feedback=total_feedback
        )

    elif current_user.role == "facilitator":
        workshops = Workshop.query.filter_by(facilitator_id=current_user.id).order_by(Workshop.date.asc()).all()

        return render_template(
            "admin_dashboard.html",
            workshops=workshops,
            facilitators=[],
            total_workshops=len(workshops),
            total_students=0,
            total_facilitators=0,
            total_registrations=Registration.query.join(Workshop).filter(Workshop.facilitator_id == current_user.id).count(),
            total_feedback=Feedback.query.join(Workshop).filter(Workshop.facilitator_id == current_user.id).count()
        )

    registrations = Registration.query.filter_by(user_id=current_user.id).all()
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
    available_workshops = Workshop.query.filter(Workshop.date >= datetime.now().date()).limit(5).all()

    return render_template(
        "student_dashboard.html",
        registrations=registrations,
        notifications=notifications,
        available_workshops=available_workshops
    )

# --- 4. ADMIN FACILITATOR MANAGEMENT ---
@app.route("/admin/facilitators/create", methods=["GET", "POST"])
@login_required
def create_facilitator():
    if current_user.role != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))

    form = FacilitatorForm()

    if form.validate_on_submit():
        full_name = form.full_name.data.strip()
        email = form.email.data.strip().lower()

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("A user with that email already exists.", "danger")
            return redirect(url_for("create_facilitator"))

        temp_password = generate_temp_password()

        facilitator = User(
            full_name=full_name,
            email=email,
            password=generate_password_hash(temp_password),
            role="facilitator",
            popia_consent=True,
            consent_date=datetime.utcnow(),
            is_suspended=False
        )

        try:
            db.session.add(facilitator)
            db.session.commit()

            try:
                msg = Message(
                    subject="PeerHub Facilitator Account Created",
                    recipients=[email]
                )
                msg.body = f"""
Hello {full_name},

Your facilitator account has been created by the system administrator.

Login details:
Email: {email}
Temporary Password: {temp_password}

Please log in and change your password after first login.

Regards,
DUT PeerHub Admin
"""
                mail.send(msg)
                flash("Facilitator added and login details sent by email.", "success")
            except Exception as e:
                flash(f"Facilitator created, but email failed to send: {str(e)}", "warning")

            return redirect(url_for("dashboard"))

        except Exception as e:
            db.session.rollback()
            flash(f"Error creating facilitator: {str(e)}", "danger")

    return render_template("create_facilitator.html", form=form)


@app.route("/admin/facilitators/<int:user_id>/toggle-status")
@login_required
def toggle_facilitator_status(user_id):
    if current_user.role != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))

    facilitator = User.query.get_or_404(user_id)

    if facilitator.role != "facilitator":
        flash("Only facilitator accounts can be suspended.", "danger")
        return redirect(url_for("dashboard"))

    facilitator.is_suspended = not facilitator.is_suspended
    db.session.commit()

    if facilitator.is_suspended:
        flash(f"{facilitator.full_name} has been suspended.", "warning")
    else:
        flash(f"{facilitator.full_name} has been reactivated.", "success")

    return redirect(url_for("dashboard"))


# --- 5. WORKSHOP MANAGEMENT ---
@app.route("/workshop/create", methods=["GET", "POST"])
@login_required
def create_workshop():
    if current_user.role not in ["admin", "facilitator"]:
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))

    if current_user.role == "facilitator" and getattr(current_user, "is_suspended", False):
        flash("Your facilitator account is suspended. You cannot create workshops.", "danger")
        return redirect(url_for("dashboard"))

    form = WorkshopForm()

    # Only admin should choose facilitator
    if current_user.role == "admin":
        form.facilitator_id.choices = [
            (u.id, u.full_name)
            for u in User.query.filter_by(role="facilitator", is_suspended=False)
            .order_by(User.full_name.asc())
            .all()
        ]
    else:
        # Facilitator should not choose another facilitator
        form.facilitator_id.choices = [(current_user.id, current_user.full_name)]
        form.facilitator_id.data = current_user.id

    if form.validate_on_submit():
        # Auto-capture facilitator if logged-in user is a facilitator
        if current_user.role == "facilitator":
            facilitator_id = current_user.id
        else:
            facilitator_id = form.facilitator_id.data

        venue_value = form.venue.data.strip() if form.venue.data else ""
        online_link_value = form.online_link.data.strip() if form.online_link.data else ""

        if form.start_time.data >= form.end_time.data:
            flash("End time must be after start time.", "danger")
            return render_template("create_workshop.html", form=form)

        # Prevent venue double booking for in-person workshops
        if form.workshop_type.data == "In-Person":
            existing_workshop = Workshop.query.filter(
                Workshop.workshop_type == "In-Person",
                Workshop.date == form.date.data,
                Workshop.venue == venue_value,
                Workshop.start_time < form.end_time.data,
                Workshop.end_time > form.start_time.data
            ).first()

            if existing_workshop:
                flash(
                    f"Venue already booked for another workshop from "
                    f"{existing_workshop.start_time.strftime('%H:%M')} to "
                    f"{existing_workshop.end_time.strftime('%H:%M')} on "
                    f"{existing_workshop.date.strftime('%d %b %Y')}.",
                    "danger"
                )
                return render_template("create_workshop.html", form=form)

        new_workshop = Workshop(
            title=form.title.data,
            description=form.description.data,
            faculty=form.faculty.data,
            workshop_type=form.workshop_type.data,
            venue=venue_value if form.workshop_type.data == "In-Person" else "Online",
            online_link=online_link_value if form.workshop_type.data == "Online" else None,
            category=form.category.data,
            level=form.level.data,
            date=form.date.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            capacity=form.capacity.data,
            facilitator_id=facilitator_id
        )

        db.session.add(new_workshop)
        db.session.commit()
        flash("Workshop scheduled successfully.", "success")
        return redirect(url_for("dashboard"))

    return render_template("create_workshop.html", form=form)


@app.route("/workshop/<int:workshop_id>")
@login_required
def workshop_detail(workshop_id):
    workshop = Workshop.query.get_or_404(workshop_id)

    # Admin can view all workshops
    if current_user.role == "admin":
        pass

    # Facilitator can only view their own workshops
    elif current_user.role == "facilitator":
        if workshop.facilitator_id != current_user.id:
            flash("You can only view workshops assigned to you.", "danger")
            return redirect(url_for("dashboard"))

    reg = Registration.query.filter_by(user_id=current_user.id, workshop_id=workshop_id).first()
    enrolled_count = Registration.query.filter_by(workshop_id=workshop_id).count()
    registrations = Registration.query.filter_by(workshop_id=workshop_id).all()

    return render_template(
        "workshop_detail.html",
        workshop=workshop,
        is_registered=(reg is not None),
        enrolled_count=enrolled_count,
        registrations=registrations
    )

# --- 5.1 REGISTRATION & QR CODE ---
@app.route("/workshop/<int:workshop_id>/qr")
@login_required
def generate_workshop_qr(workshop_id):
    workshop = Workshop.query.get_or_404(workshop_id)

    # Only admin or the assigned facilitator can generate/view QR
    if current_user.role == "facilitator" and workshop.facilitator_id != current_user.id:
        flash("You can only access QR codes for your own workshops.", "danger")
        return redirect(url_for("dashboard"))

    if current_user.role not in ["admin", "facilitator"]:
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))

    attendance_url = url_for("scan_attendance", workshop_id=workshop.id, _external=True)

    img = qrcode.make(attendance_url)

    qr_folder = os.path.join(app.root_path, "static", "qr_codes")
    os.makedirs(qr_folder, exist_ok=True)

    file_path = os.path.join(qr_folder, f"workshop_{workshop.id}.png")
    img.save(file_path)

    return send_file(file_path, mimetype="image/png")

# --- 5.2 REGISTRATION & ATTENDANCE ---
@app.route("/attendance/scan/<int:workshop_id>")
@login_required
def scan_attendance(workshop_id):
    workshop = Workshop.query.get_or_404(workshop_id)

    # Only students should scan for attendance
    if current_user.role != "student":
        flash("Only students can mark attendance through QR scan.", "danger")
        return redirect(url_for("dashboard"))

    # Student must be registered for the workshop
    registration = Registration.query.filter_by(
        user_id=current_user.id,
        workshop_id=workshop.id
    ).first()

    if not registration:
        flash("You are not registered for this workshop.", "danger")
        return redirect(url_for("dashboard"))

    # Prevent duplicate attendance
    existing_attendance = Attendance.query.filter_by(
        user_id=current_user.id,
        workshop_id=workshop.id
    ).first()

    if existing_attendance:
        flash("Your attendance has already been marked.", "info")
        return redirect(url_for("workshop_detail", workshop_id=workshop.id))
    
    

    attendance = Attendance(
        user_id=current_user.id,
        workshop_id=workshop.id
    )
    db.session.add(attendance)
    db.session.commit()

    flash("Attendance marked successfully.", "success")
    return redirect(url_for("workshop_detail", workshop_id=workshop.id))


@app.route("/workshop/<int:workshop_id>/register")
@login_required
def register_workshop(workshop_id):
    if current_user.role != "student":
        flash("Only students can register for workshops.", "danger")
        return redirect(url_for("dashboard"))

    workshop = Workshop.query.get_or_404(workshop_id)

    current_count = Registration.query.filter_by(workshop_id=workshop_id).count()
    if current_count >= workshop.capacity:
        flash("This workshop is fully booked.", "danger")
        return redirect(url_for("workshop_detail", workshop_id=workshop_id))

    existing = Registration.query.filter_by(user_id=current_user.id, workshop_id=workshop_id).first()
    if existing:
        flash("Already registered.", "info")
        return redirect(url_for("workshop_detail", workshop_id=workshop_id))

    registration = Registration(user_id=current_user.id, workshop_id=workshop_id, status="Registered")
    db.session.add(registration)
    db.session.commit()
    flash("Successfully registered!", "success")
    return redirect(url_for("workshop_detail", workshop_id=workshop_id))


# --- 6. REPORTING & CALENDAR ---
@app.route("/admin/calendar")
@login_required
def admin_calendar():
    if current_user.role != "admin":
        return redirect(url_for("dashboard"))

    workshops = Workshop.query.all()
    events = []
    for w in workshops:
        start_iso = datetime.combine(w.date, w.start_time).isoformat()
        events.append({
            "title": f"[{w.faculty}] {w.title}",
            "start": start_iso,
            "url": url_for("workshop_detail", workshop_id=w.id)
        })

    return render_template("admin_calendar.html", events=events)


@app.route("/workshop/<int:workshop_id>/reports")
@login_required
def workshop_reports(workshop_id):
    workshop = Workshop.query.get_or_404(workshop_id)

    if current_user.role != "admin" and current_user.id != workshop.facilitator_id:
        flash("Unauthorized.", "danger")
        return redirect(url_for("dashboard"))

    attendees = Attendance.query.filter_by(workshop_id=workshop_id).all()
    feedbacks = Feedback.query.filter_by(workshop_id=workshop_id).all()
    registrations = Registration.query.filter_by(workshop_id=workshop_id).all()

    return render_template(
        "workshop_reports.html",
        workshop=workshop,
        attendees=attendees,
        feedbacks=feedbacks,
        registrations=registrations
    )


# --- 7. NOTIFICATIONS & FEEDBACK ---
@app.route("/workshop/<int:workshop_id>/broadcast", methods=["POST"])
@login_required
def broadcast_message(workshop_id):
    workshop = Workshop.query.get_or_404(workshop_id)
    message_content = request.form.get("message")

    if current_user.role not in ["admin", "facilitator"]:
        flash("Unauthorized.", "danger")
        return redirect(url_for("dashboard"))

    registrations = Registration.query.filter_by(workshop_id=workshop_id).all()
    recipients = [reg.user.email for reg in registrations]

    if recipients:
        try:
            msg = Message(f"Update: {workshop.title}", recipients=recipients)
            msg.body = f"An update regarding venue/time was posted: {message_content}"
            mail.send(msg)

            for reg in registrations:
                note = Notification(user_id=reg.user_id, workshop_id=workshop_id, message=message_content)
                db.session.add(note)

            db.session.commit()
            flash("Broadcast sent to all students!", "success")
        except Exception:
            flash("Internal notification saved, but email failed.", "warning")

    return redirect(url_for("workshop_detail", workshop_id=workshop_id))


@app.route("/notification/read/<int:notification_id>")
@login_required
def mark_read(notification_id):
    note = Notification.query.get_or_404(notification_id)
    if note.user_id == current_user.id:
        note.is_read = True
        db.session.commit()
    return redirect(url_for("dashboard"))


@app.route("/workshop/<int:workshop_id>/feedback", methods=["GET", "POST"])
@login_required
def submit_feedback(workshop_id):
    if current_user.role != "student":
        flash("Only students can submit feedback.", "danger")
        return redirect(url_for("dashboard"))

    workshop = Workshop.query.get_or_404(workshop_id)
    if not workshop.is_over():
        flash("Feedback opens after the session ends.", "warning")
        return redirect(url_for("workshop_detail", workshop_id=workshop_id))

    form = FeedbackForm()
    if form.validate_on_submit():
        fb = Feedback(
            user_id=current_user.id,
            workshop_id=workshop_id,
            rating=form.rating.data,
            comment=form.comment.data
        )
        db.session.add(fb)
        db.session.commit()
        flash("Thank you!", "success")
        return redirect(url_for("dashboard"))

    return render_template("feedback.html", form=form, workshop=workshop)


# --- 8. ATTENDANCE ---
@app.route("/attendance/mark/<int:workshop_id>/<int:student_id>")
@login_required
def mark_attendance(workshop_id, student_id):
    if current_user.role not in ["admin", "facilitator"]:
        flash("Unauthorized.", "danger")
        return redirect(url_for("dashboard"))

    workshop = Workshop.query.get_or_404(workshop_id)

    if current_user.role == "facilitator" and workshop.facilitator_id != current_user.id:
        flash("You can only manage attendance for your own workshops.", "danger")
        return redirect(url_for("dashboard"))

    existing = Attendance.query.filter_by(user_id=student_id, workshop_id=workshop_id).first()
    if not existing:
        db.session.add(Attendance(user_id=student_id, workshop_id=workshop_id))
        db.session.commit()
        flash("Marked present.", "success")

    return redirect(url_for("workshop_detail", workshop_id=workshop_id))


if __name__ == "__main__":
    app.run(debug=True)
