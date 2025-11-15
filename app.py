import os
from flask import Flask, request, redirect, session, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, join_room
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message

# ----------------------------------------------------
# CONFIG
# ----------------------------------------------------
app = Flask(__name__)
app.secret_key = "team_secret_key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///team_workspace.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

# Email Setup (Gmail App Password)
app.config['MAIL_SERVER'] = "smtp.gmail.com"
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = "keshavareddymuga@gmail.com"
app.config['MAIL_PASSWORD'] = "qsggsnebvaafshqb"
app.config['MAIL_DEFAULT_SENDER'] = "keshavareddymuga@gmail.com"

mail = Mail(app)
db = SQLAlchemy(app)
socketio = SocketIO(app, async_mode="threading")

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# ----------------------------------------------------
# CSS + SweetAlert
# ----------------------------------------------------
STYLE = """
<link href='https://cdn.jsdelivr.net/npm/@sweetalert2/theme-dark@5/dark.css' rel='stylesheet'>
<script src='https://cdn.jsdelivr.net/npm/sweetalert2@11'></script>

<style>
body {
    font-family: Arial;
    background: linear-gradient(135deg,#9b5de5,#f15bb5,#00bbf9,#00f5d4);
    padding: 30px; margin: 0; background-attachment: fixed;
}
.container {
    background: #f5e9ff; padding:25px; border-radius:14px;
    max-width:820px; margin:auto; box-shadow:0 0 25px rgba(0,0,0,0.2);
}
label { font-weight:bold; margin-top:12px; display:block; }
input {
    width:100%; padding:12px; margin-top:5px;
    border-radius:8px; border:1px solid #bbb;
}
button {
    width:100%; padding:12px; margin-top:12px;
    border-radius:10px; border:none; cursor:pointer;
    color:#fff; background:linear-gradient(45deg,#000,#444);
}
button.small { width:auto; padding:8px 14px; font-size:14px; }
.row { display:flex; gap:12px; flex-wrap:wrap; }
a { text-decoration:none; color:#1a73e8; }
a:hover { text-decoration:underline; }
.notify-msg { color:green; font-weight:bold; }
</style>
"""

# ----------------------------------------------------
# MODELS
# ----------------------------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    email = db.Column(db.String(200), unique=True)
    password = db.Column(db.String(200))

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    weeks = db.Column(db.Integer)
    current_week = db.Column(db.Integer, default=1)

class ProjectWeek(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer)
    week_number = db.Column(db.Integer)
    file_name = db.Column(db.String(300))
    uploaded_by = db.Column(db.String(200))
    description = db.Column(db.Text)
    go_next_members = db.Column(db.Text, default="")

# ----------------------------------------------------
# EMAIL HELPER
# ----------------------------------------------------
def send_email_to_all(subject, body):
    try:
        emails = [u.email for u in User.query.all()]
        if emails:
            mail.send(Message(subject, recipients=emails, body=body))
    except:
        print("Email error")

# ----------------------------------------------------
# HOME
# ----------------------------------------------------
@app.route("/")
def home():
    return STYLE + """
    <div class='container'>
        <h2>Team Workspace Organizer</h2>
        <a href='/login'><button class='small'>Login</button></a>
        <a href='/register'><button class='small'>Register</button></a>
    </div>
"""

# ----------------------------------------------------
# REGISTER
# ----------------------------------------------------
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"].lower()
        pwd = request.form["password"]

        if User.query.filter_by(email=email).first():
            return STYLE + """
            <div class='container'>
                <h3>Email already exists.</h3>
                <a href='/login'><button class='small'>Login</button></a>
                <a href='/register'><button class='small'>Try Again</button></a>
            </div>
"""

        user = User(name=name, email=email, password=pwd)
        db.session.add(user)
        db.session.commit()

        return redirect("/login")

    return STYLE + """
    <div class='container'>
        <h2>Register</h2>
        <form method='POST'>
            <label>Name</label><input name='name'>
            <label>Email</label><input name='email'>
            <label>Password</label><input type='password' name='password'>
            <button>Register</button>
        </form>
    </div>
"""

# ----------------------------------------------------
# LOGIN
# ----------------------------------------------------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].lower()
        pwd = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if not user or user.password != pwd:
            return STYLE + """
            <div class='container'>
                <h3>Invalid login.</h3>
                <a href='/login'><button class='small'>Try Again</button></a>
                <a href='/register'><button class='small'>Register</button></a>
            </div>
"""

        session["user_id"] = user.id
        session["user_name"] = user.name
        return redirect("/dashboard")

    return STYLE + """
    <div class='container'>
        <h2>Login</h2>
        <form method='POST'>
            <label>Email</label><input name='email'>
            <label>Password</label><input type='password' name='password'>
            <button>Login</button>
        </form>
    </div>
"""

# ----------------------------------------------------
# LOGOUT
# ----------------------------------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ----------------------------------------------------
# DASHBOARD
# ----------------------------------------------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    projects = Project.query.all()

    proj_html = "".join(
        [f"<li><a href='/project/{p.id}'>{p.name}</a> — {p.weeks} Weeks</li>" for p in projects]
    )

    return STYLE + f"""
    <div class='container'>
        <h2>Welcome {session['user_name']}</h2>

        <h3>Create Project</h3>
        <form method='POST' action='/create_project'>
            <label>Project Name</label><input name='name'>
            <label>Weeks</label><input type='number' name='weeks' min='1'>
            <button>Create Project</button>
        </form>

        <h3>Your Projects</h3>
        <ul>{proj_html or "No projects yet"}</ul>

        <a href='/logout'><button class='small'>Logout</button></a>
    </div>
"""

# ----------------------------------------------------
# CREATE PROJECT
# ----------------------------------------------------
@app.route("/create_project", methods=["POST"])
def create_project():
    name = request.form["name"]
    weeks = int(request.form["weeks"])

    p = Project(name=name, weeks=weeks)
    db.session.add(p)
    db.session.commit()

    for w in range(1, weeks+1):
        db.session.add(ProjectWeek(project_id=p.id, week_number=w))
    db.session.commit()

    return redirect("/dashboard")

# ----------------------------------------------------
# DOWNLOAD
# ----------------------------------------------------
@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# ----------------------------------------------------
# PROJECT PAGE
# ----------------------------------------------------
@app.route("/project/<int:pid>", methods=["GET","POST"])
def project_page(pid):
    if "user_id" not in session:
        return redirect("/login")

    p = Project.query.get(pid)
    week = p.current_week
    pw = ProjectWeek.query.filter_by(project_id=pid, week_number=week).first()

    # File upload
    if request.method == "POST":
        f = request.files["file"]
        desc = request.form["description"]

        if f.filename:
            fname = secure_filename(f.filename)
            f.save(os.path.join(app.config["UPLOAD_FOLDER"], fname))

            pw.file_name = fname
            pw.uploaded_by = session["user_name"]
            pw.description = desc
            db.session.commit()

            return redirect(f"/project/{pid}")

    # Go Next
    if request.args.get("go_next"):
        uid = str(session["user_id"])
        clicked = pw.go_next_members.split(",") if pw.go_next_members else []

        if uid not in clicked:
            clicked.append(uid)
            pw.go_next_members = ",".join(clicked)
            db.session.commit()

        if len(clicked) == User.query.count():
            if p.current_week < p.weeks:
                p.current_week += 1
                pw.go_next_members = ""
                db.session.commit()
            else:
                return redirect(f"/project_completed/{pid}")

        return redirect(f"/project/{pid}")

    # File Section
    file_html = f"""
    <p><b>{pw.uploaded_by}</b> uploaded {pw.file_name}
    — <a href='/download/{pw.file_name}'>Download</a><br>{pw.description}</p>
    """ if pw.file_name else "<p>No files yet</p>"

    clicked_names = []
    for uid in pw.go_next_members.split(","):
        if uid.isdigit():
            u = User.query.get(int(uid))
            if u:
                clicked_names.append(u.name)

    return STYLE + f"""
    <div class='container'>
        <h2>{p.name} — Week {week}/{p.weeks}</h2>

        {file_html}

        <form method='POST' enctype='multipart/form-data'>
            <label>Select File</label><input type='file' name='file'>
            <label>Description</label><input name='description'>
            <button>Upload</button>
        </form>

        <a href='?go_next=1'>
            <button class='small'>
                {"Finish Project" if week==p.weeks else "Go Next Week"}
            </button>
        </a>

        <p class='small-note'><b>Members who clicked:</b> 
            {", ".join(clicked_names) if clicked_names else "None yet"}
        </p>

        <div class='row'>
            <a href='/dashboard'><button class='small'>Back</button></a>
            <a href='/logout'><button class='small'>Logout</button></a>
        </div>
    </div>
"""

# ----------------------------------------------------
# PROJECT COMPLETED
# ----------------------------------------------------
@app.route("/project_completed/<int:pid>")
def project_completed(pid):
    p = Project.query.get(pid)
    return STYLE + f"""
    <div class='container'>
        <h2>Project Completed 🎉</h2>
        <h3>{p.name} is finished</h3>
        <a href='/dashboard'><button>Back</button></a>
    </div>
"""

# ----------------------------------------------------
# RUN
# ----------------------------------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    # IMPORTANT FOR RENDER: disable eventlet and use threading
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, use_reloader=False)
