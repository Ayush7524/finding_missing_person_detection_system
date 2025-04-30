from flask import Flask, request, redirect, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, time
from flask import Flask, render_template, request, redirect, url_for, session, flash
from sqlalchemy import func, desc

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///missing_persons.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "supersecretkey"  # 🔐 Change this in production
db = SQLAlchemy(app)


class MissingPerson(db.Model):
    __tablename__ = 'missing_persons'
    id = db.Column(db.Integer, primary_key=True)
    person_name = db.Column(db.String(100), unique=True, nullable=False)
    image_path = db.Column(db.String(255))
    age = db.Column(db.Integer)
    height = db.Column(db.Integer)
    weight = db.Column(db.Integer)
    address = db.Column(db.String(255))
    missing_date = db.Column(db.Date)
    missing_time = db.Column(db.Time)
    missing_from_address = db.Column(db.String(255))
    price = db.Column(db.Integer)
    gender = db.Column(db.String(20))

    last_seen = db.relationship("LastSeenInfo", backref="person", uselist=False, cascade="all, delete")


class LastSeenInfo(db.Model):
    __tablename__ = 'last_seen_info'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime)
    location = db.Column(db.String(255))
    person_id = db.Column(db.Integer, db.ForeignKey('missing_persons.id'), nullable=False)


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    password = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"


with app.app_context():
    db.create_all()

# -------------------
# Routes
# -------------------


@app.route("/account",  methods=["GET"])
def account():
    if session["user_id"] is None:
        return redirect("/")
    
    subq = (
        db.session.query(
            LastSeenInfo.person_id,
            func.max(LastSeenInfo.timestamp).label("latest_seen")
        )
        .group_by(LastSeenInfo.person_id)
        .subquery()
    )

    # Join MissingPerson with subquery and order by timestamp desc
    results = (
        db.session.query(MissingPerson, subq.c.latest_seen)
        .outerjoin(subq, MissingPerson.id == subq.c.person_id)
        .order_by(desc(subq.c.latest_seen))
        .all()
    )

    print(results)

    return render_template("account.html", results=results)




@app.route("/register", methods=["GET", "POST"])
def register_user():
    if request.method == "POST":
        username = request.form.get("name")
        phone = request.form.get("phone")
        password = request.form.get("password")

        if User.query.filter_by(username=username).first():
            return "Username already exists"

        new_user = User(username=username, phone=phone, password=password)
        db.session.add(new_user)
        db.session.commit()
        user = User.query.filter_by(phone=phone).first()
        session["user_id"] = user.id
        session["username"] = user.username
        flash("User registered successfully!.", "success")
        return redirect(url_for("account"))

    return render_template("register.html")


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        phone = request.form.get("phone")
        password = request.form.get("pass")

        user = User.query.filter_by(phone=phone).first()
        print("user", user.password, password)
        if user and user.password == password:
            session["user_id"] = user.id
            session["username"] = user.username
            flash("Logged in successfully.", "success")
            return redirect("/account")
        else:
            flash("Invalid username or password.", "danger")

    return render_template("index.html")


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session["user_id"] = None
    session["username"] = None

    return redirect("/")

# Handle form POST
@app.route("/register_missing", methods=["POST", "GET"])
def register_person():
    if session["user_id"] is None:
        return redirect("/")
    if request.method == "POST":
        # Parse missing_date and missing_time properly
        missing_date_str = request.form.get('missing_date')
        missing_time_str = request.form.get('missing_time')

        missing_date = None
        missing_time = None

        if missing_date_str:
            missing_date = datetime.strptime(missing_date_str, "%Y-%m-%d").date()

        if missing_time_str:
            missing_time = datetime.strptime(missing_time_str, "%H:%M").time()

        person = MissingPerson(
            person_name=request.form['person_name'],
            image_path=request.form.get('image_path'),
            age=request.form.get('age'),
            height=request.form.get('height'),
            weight=request.form.get('weight'),
            address=request.form.get('address'),
            missing_date=missing_date,
            missing_time=missing_time,
            missing_from_address=request.form.get('missing_from_address'),
            price=request.form.get('price'),
            gender=request.form.get('gender')
        )
        db.session.add(person)
        db.session.commit()
        return redirect("/account")
    
    return render_template("register_missing.html")



@app.route("/history/<int:person_id>")
def last_seen_history(person_id):
    if session["user_id"] is None:
        return redirect("/")
    person = MissingPerson.query.get_or_404(person_id)
    history = (
        LastSeenInfo.query
        .filter_by(person_id=person_id)
        .order_by(LastSeenInfo.timestamp.desc())
        .all()
    )
    return render_template("history.html", person=person, history=history)




@app.route("/api/add_last_seen", methods=["POST"])
def add_last_seen():
    data = request.get_json()

    image_path = data.get('image_path')
    location = data.get('location')
    timestamp = data.get('timestamp')

    if not image_path or not location or not timestamp:
        return jsonify({"error": "Missing fields"}), 400

    person = MissingPerson.query.filter_by(image_path=image_path).first()
    if not person:
        return jsonify({"error": "Person not found"}), 404

    # Check if any existing record for this person at this location
    existing = LastSeenInfo.query.filter_by(person_id=person.id, location=location).first()

    if existing:
        # Same location → update timestamp
        existing.timestamp = datetime.fromisoformat(timestamp)
        db.session.commit()
        return jsonify({"message": "Last seen timestamp updated for existing location"}), 200
    else:
        # New location → create new entry
        new_entry = LastSeenInfo(
            timestamp=datetime.fromisoformat(timestamp),
            location=location,
            person_id=person.id
        )
        db.session.add(new_entry)
        db.session.commit()
        return jsonify({"message": "New last seen location entry added"}), 201


if __name__ == "__main__":
    app.run(debug=True)
