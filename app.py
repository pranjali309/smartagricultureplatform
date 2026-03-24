from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
from flask_mysqldb import MySQL
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from apscheduler.schedulers.background import BackgroundScheduler

from datetime import datetime
import os
import re
import random
import time
import threading


# ===================== Flask Setup =====================
app = Flask(__name__)
app.secret_key = "your_secret_key"

# ===================== MySQL Configuration =====================
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'agriculture_db'

mysql = MySQL(app)
# ===================== SQLAlchemy Configuration =====================
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:root@localhost/agriculture_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ===================== User Model =====================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

# ===================== File Upload Path =====================
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ===================== Allowed Extensions =====================
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ===================== Auto Create Tables (crops, recommendations) =====================
def create_support_tables():
    cur = mysql.connection.cursor()
    # crops table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS crops (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(150),
            image VARCHAR(255),
            description TEXT,
            duration VARCHAR(100),
            fertilizer VARCHAR(255),
            expected_profit FLOAT,
            sowing_season VARCHAR(100),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # recommendations table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            soil_type VARCHAR(100),
            nitrogen FLOAT,
            phosphorus FLOAT,
            potassium FLOAT,
            ph FLOAT,
            temperature FLOAT,
            humidity FLOAT,
            rainfall FLOAT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    mysql.connection.commit()
    cur.close()

with app.app_context():
    create_support_tables()

# ===================== Register =====================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form['fullname'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        phone = request.form['phone']
        address = request.form['address']
        photo = request.files.get('profile_photo')

        if not fullname or not email or not password or not phone or not address:
            flash("All fields are required!", "danger")
            return redirect(url_for('register'))

        if not re.fullmatch(r'^(\d{10}|\d{12})$', phone):
            flash("Phone number must be 10 or 12 digits.", "danger")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        photo_path = None
        if photo and photo.filename != '' and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            photo_path = filename
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                INSERT INTO users (fullname, email, password, phone, address, profile_photo)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (fullname, email, hashed_password, phone, address, photo_path))
            mysql.connection.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            flash("Database error: " + str(e), "danger")
        finally:
            cur.close()

    return render_template('register.html')
from werkzeug.security import check_password_hash

# ===================== Login =====================

# ===================== Login =====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT id, email, password, role FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[2], password):
            # Login successful
            session['user'] = user[1]   # email
            session['role'] = user[3]   # role

            # Role-based redirect
            if user[3] == 'admin':
                return redirect(url_for('admin_dashboard'))   # Admin dashboard
            else:
                return redirect(url_for('home'))             # Normal user → index page
        else:
            flash("Invalid email or password", "danger")

    return render_template('login.html')



# ===================== Forgot Password =====================
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for('forgot_password'))

        hashed_new_password = generate_password_hash(new_password)
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()

        if user:
            cur.execute("UPDATE users SET password=%s WHERE email=%s", (hashed_new_password, email))
            mysql.connection.commit()
            flash("Password updated successfully! Please login.", "success")
            cur.close()
            return redirect(url_for('login'))
        else:
            flash("Email not found!", "danger")
            cur.close()

    return render_template('forgot_password.html')

# ===================== Static Pages =====================
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/ai-services')
def ai_services():
    return render_template('ai_services.html')

@app.route('/farmer-connect')
def farmer_connect():
    return render_template('farmer_connect.html')

# Database table
class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(12), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Create tables
with app.app_context():
    db.create_all()

# Contact page route
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        message = request.form['message']

        # Basic validations
        if len(phone) > 12:
            flash("Phone number cannot exceed 12 characters.", "danger")
            return redirect(url_for('contact'))

        if '@' not in email or '.' not in email:
            flash("Please enter a valid email address.", "danger")
            return redirect(url_for('contact'))

        # Save to database
        new_contact = Contact(name=name, email=email, phone=phone, message=message)
        db.session.add(new_contact)
        db.session.commit()

        flash("Your message has been sent! We'll reply shortly.", "success")
        return redirect(url_for('contact'))

    return render_template('contact.html')

# ===================== Admin Dashboard =====================
from collections import Counter
from flask import Flask, render_template
from flask_mysqldb import MySQL
import json

@app.route('/admin/dashboard')
def admin_dashboard():
    cur = mysql.connection.cursor()

    # Overview counts
    cur.execute("SELECT COUNT(*) FROM users")
    users_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM prices")
    market_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM farm_data")
    weather_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM ecommerce_tools_usage")
    ai_tools_count = cur.fetchone()[0]

    # AI Tools Usage Over Time
    cur.execute("SELECT created_at FROM ecommerce_tools_usage ORDER BY created_at")
    ai_dates_raw = [row[0].strftime('%Y-%m-%d') for row in cur.fetchall()]
    ai_dates = sorted(set(ai_dates_raw))
    ai_counts = [ai_dates_raw.count(date) for date in ai_dates]

    # Platform-wise Pie Chart
    cur.execute("SELECT platform_name FROM ecommerce_tools_usage")
    platforms = [row[0] for row in cur.fetchall()]
    platform_counter = Counter(platforms)
    platform_labels = list(platform_counter.keys())
    platform_values = list(platform_counter.values())

    # User Activity Distribution
    cur.execute("SELECT email FROM user_activity")
    emails = [row[0] for row in cur.fetchall()]
    email_counter = Counter(emails)
    user_labels = list(email_counter.keys())
    user_values = list(email_counter.values())

    return render_template(
        'admin/admin_dashboard.html',
        users_count=users_count,
        market_count=market_count,
        weather_count=weather_count,
        ai_tools_count=ai_tools_count,
        ai_dates=ai_dates,
        ai_counts=ai_counts,
        platform_labels=json.dumps(platform_labels),
        platform_values=json.dumps(platform_values),
        user_labels=json.dumps(user_labels),
        user_values=json.dumps(user_values)
    )



# ===================== User Profile =====================

# Demo user data
user_data = {
    "name": "Pranjali Nikam",
    "email": "pranjal@299gmail.com",
    "phone": "7892868345",
    "address": "Nikamwadi",
    "photo": "default.png",
    "password": "12345"
}


@app.route('/profile', methods=['GET'])
def profile():
    return render_template('profile.html', 
                           name=user_data['name'],
                           email=user_data['email'],
                           phone=user_data['phone'],
                           address=user_data['address'],
                           photo=user_data['photo'])

@app.route('/update-profile', methods=['POST'])
def update_profile():
    # Update info
    user_data['name'] = request.form.get('name', user_data['name'])
    user_data['email'] = request.form.get('email', user_data['email'])
    user_data['phone'] = request.form.get('phone', user_data['phone'])
    user_data['address'] = request.form.get('address', user_data['address'])

    # Profile photo
    if 'profile_photo' in request.files:
        file = request.files['profile_photo']
        if file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            user_data['photo'] = filename

    return redirect(url_for('profile'))

@app.route('/change-password', methods=['POST'])
def change_password():
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if new_password and new_password == confirm_password:
        user_data['password'] = new_password
        return """
        <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; 
                    height:100vh; font-family:Arial, sans-serif; background-color:#f8f9fa;">
            <h3 style="color:#28a745;">Password updated successfully!</h3>
            <a href='/profile' style="margin-top:10px; text-decoration:none; color:#fff; 
                                      background-color:#007bff; padding:10px 20px; border-radius:5px;">Back to Profile</a>
        </div>
        """
    else:
        return """
        <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; 
                    height:100vh; font-family:Arial, sans-serif; background-color:#f8f9fa;">
            <h3 style="color:#dc3545;">Passwords do not match!</h3>
            <a href='/profile' style="margin-top:10px; text-decoration:none; color:#fff; 
                                      background-color:#007bff; padding:10px 20px; border-radius:5px;">Back to Profile</a>
        </div>
        """

# ===================== Logout =====================
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

# ===================== Admin Add Crop =====================
@app.route('/admin/add_crop', methods=['GET', 'POST'])
def add_crop():
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied!", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        duration = request.form.get('duration', '').strip()
        fertilizer = request.form.get('fertilizer', '').strip()
        expected_profit = request.form.get('expected_profit') or 0
        sowing_season = request.form.get('sowing_season', '').strip()
        description = request.form.get('description', '').strip()
        image = request.files.get('image')

        if not name:
            flash("Crop name is required.", "danger")
            return redirect(url_for('add_crop'))

        image_filename = None
        if image and image.filename != '' and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_filename = filename

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO crops (name, image, description, duration, fertilizer, expected_profit, sowing_season)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (name, image_filename, description, duration, fertilizer, expected_profit, sowing_season))
        mysql.connection.commit()
        cur.close()

        flash("Crop added successfully!", "success")
        return redirect(url_for('view_crops'))

    return render_template('admin/add_crop.html')

# ===================== Admin View Crops =====================
@app.route('/admin/view_crops')
def view_crops():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, name, image, description, duration, fertilizer, expected_profit, sowing_season FROM crops ORDER BY created_at DESC")
    crops = cur.fetchall()
    cur.close()
    return render_template('admin/view_crops.html', crops=crops)

@app.route('/crop/<int:crop_id>')
def crop_details(crop_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM crops WHERE id = %s", (crop_id,))
    crop = cur.fetchone()
    cur.close()

    if not crop:
        return "Crop not found", 404

    return render_template('admin/crop_details.html', crop=crop)

# ===================== Admin Manage Crops =====================
@app.route('/admin/manage_crops')
def manage_crops():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, name, image, description, duration, fertilizer, expected_profit, sowing_season FROM crops ORDER BY created_at DESC")
    crops = cur.fetchall()
    cur.close()
    return render_template('admin/manage_crops.html', crops=crops)

# ===================== Edit Crop =====================
@app.route('/admin/edit_crop/<int:crop_id>', methods=['GET', 'POST'])
def edit_crop(crop_id):
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied!", "danger")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM crops WHERE id=%s", (crop_id,))
    crop = cur.fetchone()

    if not crop:
        flash("Crop not found.", "warning")
        cur.close()
        return redirect(url_for('manage_crops'))

    if request.method == 'POST':
        name = request.form.get('name')
        duration = request.form.get('duration')
        fertilizer = request.form.get('fertilizer')
        expected_profit = request.form.get('expected_profit')
        sowing_season = request.form.get('sowing_season')
        description = request.form.get('description')
        image = request.files.get('image')

        image_filename = crop[2]  # existing image
        if image and image.filename != '' and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_filename = filename

        cur.execute("""
            UPDATE crops 
            SET name=%s, image=%s, description=%s, duration=%s, fertilizer=%s, expected_profit=%s, sowing_season=%s
            WHERE id=%s
        """, (name, image_filename, description, duration, fertilizer, expected_profit, sowing_season, crop_id))
        mysql.connection.commit()
        cur.close()
        flash("Crop updated successfully!", "success")
        return redirect(url_for('manage_crops'))

    cur.close()
    return render_template('admin/edit_crop.html', crop=crop)


# ===================== Delete Crop =====================
@app.route('/admin/delete_crop/<int:crop_id>')
def delete_crop(crop_id):
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied!", "danger")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM crops WHERE id=%s", (crop_id,))
    mysql.connection.commit()
    cur.close()
    flash("Crop deleted successfully!", "success")
    return redirect(url_for('manage_crops'))

# =============================tools============================

def log_user_activity(tool_name):
    if 'email' in session:
        email = session['email']
    else:
        email = 'guest'

    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent')

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO user_activity (email, tool_name, ip_address, user_agent)
        VALUES (%s, %s, %s, %s)
    """, (email, tool_name, ip_address, user_agent))
    mysql.connection.commit()
    cur.close()

# ===================== Crop Recommendation =====================
# ===================== Crop Recommendation (FIXED) =====================
from flask_mysqldb import MySQLdb

@app.route('/crop_recommendation', methods=['GET', 'POST'])
def crop_recommendation():
    recommendation_results = []

    if request.method == 'POST':
        soil_type = request.form['soil_type']
        nitrogen = float(request.form['nitrogen'])
        phosphorus = float(request.form['phosphorus'])
        potassium = float(request.form['potassium'])
        ph = float(request.form['ph'])
        temperature = float(request.form['temperature'])
        humidity = float(request.form['humidity'])
        rainfall = float(request.form['rainfall'])

        # -------- Save user input --------
        try:
            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO recommendations
                (soil_type, nitrogen, phosphorus, potassium, ph,
                 temperature, humidity, rainfall, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                soil_type, nitrogen, phosphorus, potassium, ph,
                temperature, humidity, rainfall, datetime.now()
            ))
            mysql.connection.commit()
            cur.close()
        except Exception as e:
            flash(f"Error saving data: {str(e)}", "danger")

        # -------- Fetch recommended crops (DICT CURSOR) --------
        try:
            cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cur.execute("""
                SELECT id, name, image, description, duration,
                       fertilizer, expected_profit, sowing_season
                FROM crops
                ORDER BY expected_profit DESC
                LIMIT 6
            """)
            recommendation_results = cur.fetchall()
            cur.close()
        except Exception as e:
            flash(f"Error fetching crops: {str(e)}", "danger")

    return render_template(
        'crop_recommendation.html',
        recommendation_results=recommendation_results
    )

# ================= Admin Recommendations Page =================
# ADMIN PAGE EXAMPLE
from flask_mysqldb import MySQL, MySQLdb
from flask import Flask, render_template, session, flash, redirect

# ---------------- ADMIN: Show Stored Recommendations -----------------
@app.route('/admin/recommendations')
def admin_recommendations():
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied. Admins only!", "danger")
        return redirect('/login')
    
    # Use DictCursor to get dictionary results
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM recommendations ORDER BY id DESC")
    recs = cur.fetchall()
    cur.close()
    
    return render_template('admin/recommendations.html', recs=recs)

from datetime import datetime

class Recommendation(db.Model):
    __tablename__ = 'recommendations'
    id = db.Column(db.Integer, primary_key=True)
    soil_type = db.Column(db.String(50))
    nitrogen = db.Column(db.Float)
    phosphorus = db.Column(db.Float)
    potassium = db.Column(db.Float)
    ph = db.Column(db.Float)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    rainfall = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/admin/recommendation/edit/<int:rec_id>', methods=['GET', 'POST'])
def edit_recommendation(rec_id):
    rec = Recommendation.query.get_or_404(rec_id)
    if request.method == 'POST':
        rec.soil_type = request.form['soil_type']
        rec.nitrogen = request.form['nitrogen']
        rec.phosphorus = request.form['phosphorus']
        rec.potassium = request.form['potassium']
        rec.ph = request.form['ph']
        rec.temperature = request.form['temperature']
        rec.humidity = request.form['humidity']
        rec.rainfall = request.form['rainfall']
        db.session.commit()
        flash("Recommendation updated successfully!", "success")
        return redirect(url_for('admin_recommendations'))

    return render_template('admin/edit_recommendation.html', rec=rec)


@app.route('/admin/recommendation/delete/<int:rec_id>')
def delete_recommendation(rec_id):
    rec = Recommendation.query.get_or_404(rec_id)
    db.session.delete(rec)
    db.session.commit()
    flash("Recommendation deleted successfully!", "success")
    return redirect(url_for('admin_recommendations'))


@app.route('/yield-prediction', methods=['GET', 'POST'])
def yield_prediction():
    log_user_activity('Yield Prediction')

    predicted_yield = None

    if request.method == 'POST':
        crop_name = request.form.get('crop_name')
        soil_type = request.form.get('soil_type')

        rainfall = float(request.form.get('rainfall') or 0)
        temperature = float(request.form.get('temperature') or 0)
        humidity = float(request.form.get('humidity') or 0)
        fertilizer = float(request.form.get('fertilizer') or 0)

        base_yield = 2.5
        if crop_name.lower() == 'rice':
            base_yield = 3.0
        elif crop_name.lower() == 'wheat':
            base_yield = 2.8
        elif crop_name.lower() == 'maize':
            base_yield = 2.6

        yield_factor = (rainfall / 1000) + (temperature / 100) + (humidity / 200) + (fertilizer / 500)
        predicted_yield = round(base_yield * yield_factor, 2)

        # --- SAVE TO DATABASE ---
        try:
            user_email = session.get('user', 'guest')   # <-- FIXED HERE

            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO yield_prediction_usage
                (user_email, crop_name, soil_type, rainfall, temperature, humidity, fertilizer, predicted_yield)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                user_email,
                crop_name,
                soil_type,
                rainfall,
                temperature,
                humidity,
                fertilizer,
                predicted_yield
            ))
            mysql.connection.commit()
            cur.close()
        except Exception as e:
            print("Error saving yield prediction:", e)

        return render_template('yield_prediction.html', predicted_yield=predicted_yield)

    return render_template('yield_prediction.html', predicted_yield=None)

# ===================== Disease Detection =====================
@app.route('/disease-detection', methods=['GET', 'POST'])
def disease_detection():
    log_user_activity('disease-detection')
    predicted_disease = None
    remedy = None
    image_filename = None

    if request.method == 'POST':
        image = request.files.get('leaf_image')

        if image and image.filename != '':
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_filename = filename

            # --- Random disease prediction logic ---
            possible_diseases = [
                ("Leaf Blight", "Use Mancozeb or Copper-based fungicide, and avoid overhead watering."),
                ("Powdery Mildew", "Apply Sulfur-based spray and ensure proper air circulation."),
                ("Rust Disease", "Use Propiconazole spray and remove affected leaves."),
                ("Bacterial Spot", "Use Copper hydroxide spray, avoid wetting leaves."),
                ("Healthy Leaf", "No disease detected! Your crop looks healthy 🌱."),
                ("Downy Mildew", "Spray with Metalaxyl and reduce humidity around plants."),
                ("Early Blight", "Apply Chlorothalonil or Mancozeb spray and remove infected leaves.")
            ]

            predicted_disease, remedy = random.choice(possible_diseases)

            # --- SAVE TO DATABASE ---
            try:
                cur = mysql.connection.cursor()
                cur.execute("""
                    INSERT INTO disease_detection_usage
                    (user_email, image, predicted_disease, remedy)
                    VALUES (%s, %s, %s, %s)
                """, (session.get('email', 'guest'), image_filename, predicted_disease, remedy))
                mysql.connection.commit()
                cur.close()
            except Exception as e:
                print("Error saving disease detection:", e)

        else:
            flash("Please upload a leaf image first!", "warning")

    return render_template(
        'disease_detection.html',
        predicted_disease=predicted_disease,
        remedy=remedy,
        image_filename=image_filename
    )




@app.route('/seed-quality', methods=['GET', 'POST'])
def seed_quality():
    log_user_activity('seed-quality')
    predicted_viability = None
    recommendation = None
    image_filename = None
    seed_type = None
    sample_size = None
    moisture = None
    purity = None

    if request.method == 'POST':
        seed_type = request.form.get('seed_type')
        try:
            sample_size = int(request.form.get('sample_size') or 0)
        except ValueError:
            sample_size = 0
        try:
            moisture = float(request.form.get('moisture') or 0)
        except ValueError:
            moisture = 0.0
        try:
            purity = float(request.form.get('purity') or 0)
        except ValueError:
            purity = 0.0

        # image save
        img = request.files.get('seed_image')
        if img and img.filename != '':
            filename = secure_filename(img.filename)
            img.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_filename = filename

        # --- Mock viability logic ---
        base = purity
        if moisture > 12:
            base -= (moisture - 12) * 1.5
        uncertainty = 5.0 if sample_size < 50 else 2.5 if sample_size < 200 else 1.0
        rand_adjust = random.uniform(-uncertainty, uncertainty)
        predicted = max(0.0, min(100.0, round(base + rand_adjust, 1)))
        predicted_viability = predicted

        # Randomized Recommendations ✨
        high_quality_msgs = [
            "Excellent seed quality! Ready for sowing — maintain in a cool, dry place.",
            "High viability detected — proceed confidently with field planting.",
            "Top-notch seed batch. Store airtight to retain germination power.",
            "Healthy and viable seeds. You can directly use them for your next crop."
        ]

        medium_quality_msgs = [
            "Average seed quality. Conduct a germination test before large-scale sowing.",
            "Moderate viability — consider using slightly higher seeding density.",
            "Good but not perfect. Test a small batch before going full field.",
            "Acceptable seed condition; handle carefully during storage."
        ]

        low_quality_msgs = [
            "Low viability. It's safer to buy fresh certified seeds.",
            "Seeds appear weak — consider re-drying or replacing with new stock.",
            "Poor germination potential. Avoid using for main field sowing.",
            "Old or moisture-affected seeds. Replace for better yield."
        ]

        # choose random recommendation based on predicted viability
        if predicted_viability >= 80:
            recommendation = random.choice(high_quality_msgs)
        elif predicted_viability >= 50:
            recommendation = random.choice(medium_quality_msgs)
        else:
            recommendation = random.choice(low_quality_msgs)

        # --- SAVE TO DATABASE ---
        try:
            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO seed_quality_usage
                (user_email, seed_type, sample_size, moisture, purity, image, predicted_viability, recommendation)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (session.get('email','guest'), seed_type, sample_size, moisture, purity, image_filename, predicted_viability, recommendation))
            mysql.connection.commit()
            cur.close()
        except Exception as e:
            print("Error saving seed quality:", e)

    return render_template('seed_quality.html',
                           predicted_viability=predicted_viability,
                           recommendation=recommendation,
                           image_filename=image_filename,
                           seed_type=seed_type,
                           sample_size=sample_size,
                           moisture=moisture,
                           purity=purity)


@app.route('/rainfall-prediction', methods=['GET', 'POST'])
def rainfall_prediction():
    predicted_rainfall = None
    message = None
    months = []
    rainfall_values = []
    location = None

    if request.method == 'POST':
        location = request.form.get('location')

        # ------------------------------
        # 1️⃣ Your prediction logic here
        # Example: simple mock prediction
        import random
        predicted_rainfall = round(random.uniform(10, 100), 1)
        message = "Moderate rainfall expected." if predicted_rainfall < 50 else "Heavy rainfall expected."

        # Example monthly rainfall data for chart
        months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        rainfall_values = [random.randint(10,100) for _ in range(12)]
        # ------------------------------

        # 2️⃣ Save to database
        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                INSERT INTO rainfall_prediction_usage (user_email, location, predicted_rainfall, message, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """, (session.get('user', 'guest@example.com'), location, predicted_rainfall, message))
            mysql.connection.commit()
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error saving prediction: {str(e)}", "danger")
        finally:
            cur.close()

    return render_template(
        'rainfall_prediction.html',
        predicted_rainfall=predicted_rainfall,
        message=message,
        months=months,
        rainfall_values=rainfall_values,
        location=location
    )

@app.route('/climate-advisory', methods=['GET', 'POST'])
def climate_advisory():
    log_user_activity('climate-advisory')
    advisory = None
    temperature = None
    humidity = None
    rainfall = None

    if request.method == 'POST':
        temperature = float(request.form.get('temperature') or 0)
        humidity = float(request.form.get('humidity') or 0)
        rainfall = float(request.form.get('rainfall') or 0)

        advices = [
            "Temperature is favorable — you can start sowing new crops like maize or soybean.",
            "High humidity may lead to fungal infections — monitor and use preventive sprays.",
            "Low rainfall expected — consider irrigation or mulching to retain soil moisture.",
            "Moderate conditions detected — ideal for vegetable and cereal crop growth.",
            "Heavy rainfall ahead — ensure proper drainage to avoid waterlogging.",
            "Hot and dry climate — prefer drought-resistant crops such as millets.",
            "Stable weather — perfect time for fertilizer application and field preparation."
        ]

        import random
        advisory = random.choice(advices)

        # --- SAVE TO DATABASE ---
        try:
            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO climate_advisory_usage
                (user_email, temperature, humidity, rainfall, advisory)
                VALUES (%s,%s,%s,%s,%s)
            """, (session.get('email','guest'), temperature, humidity, rainfall, advisory))
            mysql.connection.commit()
            cur.close()
        except Exception as e:
            print("Error saving climate advisory:", e)

    return render_template(
        'climate_advisory.html',
        advisory=advisory,
        temperature=temperature,
        humidity=humidity,
        rainfall=rainfall
    )



@app.route('/mixed-crop', methods=['GET', 'POST'])
def mixed_crop():
    log_user_activity('mixed-crop')
    import random

    main_crop = None
    compatible_crops = []

    crop_suggestions = {
        'maize': ['Beans', 'Pumpkin', 'Cowpea', 'Groundnut'],
        'rice': ['Sesame', 'Soybean', 'Pigeon Pea'],
        'cotton': ['Sorghum', 'Pigeon Pea', 'Groundnut'],
        'wheat': ['Chickpea', 'Mustard', 'Lentil'],
        'sugarcane': ['Onion', 'Garlic', 'Cabbage'],
        'millet': ['Cowpea', 'Sesame', 'Green gram'],
        'soybean': ['Maize', 'Sorghum', 'Pigeon Pea']
    }

    if request.method == 'POST':
        main_crop = request.form.get('main_crop').lower()
        if main_crop in crop_suggestions:
            compatible_crops = random.sample(crop_suggestions[main_crop], k=min(3, len(crop_suggestions[main_crop])))
        else:
            # Random fallback
            all_crops = [crop for crops in crop_suggestions.values() for crop in crops]
            compatible_crops = random.sample(all_crops, 3)

        # --- SAVE TO DATABASE ---
        try:
            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO mixed_crop_usage
                (user_email, main_crop, compatible_crops)
                VALUES (%s,%s,%s)
            """, (session.get('email','guest'), main_crop, ",".join(compatible_crops)))
            mysql.connection.commit()
            cur.close()
        except Exception as e:
            print("Error saving mixed crop usage:", e)

    return render_template('mixed_crop.html', main_crop=main_crop, compatible_crops=compatible_crops)

# ===================== Water Requirement Forecasting =====================
@app.route('/water-forecast', methods=['GET', 'POST'])
def water_forecast():
    log_user_activity('Water Forecast')
    import random
    from datetime import datetime, timedelta

    crop = None
    water_need = None
    advice = None
    next_irrigation = None  # User-friendly display

    # Crop-wise irrigation logic
    crop_needs = {
        'rice': ('High', 'Maintain 5–7 cm standing water; frequent irrigation needed.', 2),
        'maize': ('Moderate', 'Irrigate at tasseling and grain filling stages.', 4),
        'cotton': ('Moderate', 'Water deeply but less frequently to promote root growth.', 5),
        'wheat': ('Low', 'Irrigate mainly during flowering and grain formation.', 6),
        'soybean': ('Moderate', 'Ensure soil moisture at pod formation.', 4),
        'sugarcane': ('High', 'Regular irrigation required every 7–10 days.', 3)
    }

    if request.method == 'POST':
        crop = request.form.get('crop', '').lower()

        if crop in crop_needs:
            water_need, advice, next_days = crop_needs[crop]
        else:
            water_need = random.choice(['Low', 'Moderate', 'High'])
            advice = "Monitor soil moisture and adjust irrigation accordingly."
            next_days = random.randint(3, 7)

        # Calculate next irrigation date
        next_irrigation_date = datetime.now() + timedelta(days=next_days)

        # MySQL-compatible date for storage
        next_irrigation_db = next_irrigation_date.strftime("%Y-%m-%d")  # 'YYYY-MM-DD'

        # User-friendly format for template
        next_irrigation = next_irrigation_date.strftime("%A, %d %B %Y")  # 'Wednesday, 10 December 2025'

        # -----------------------
        #    SAVE TO DATABASE
        # -----------------------
        try:
            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO water_forecast_usage
                (user_email, crop, water_need, advice, next_irrigation)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                session.get('email', 'guest'),
                crop,
                water_need,
                advice,
                next_irrigation_db  # <- Use DATE format for DB
            ))
            mysql.connection.commit()
            cur.close()
            print("[DEBUG] Water forecast saved successfully.")
        except Exception as e:
            print("Error saving water forecast usage:", e)

    return render_template(
        'water_forecast.html',
        crop=crop,
        water_need=water_need,
        advice=advice,
        next_irrigation=next_irrigation
    )

@app.route('/market-forecast', methods=['GET', 'POST'])
def market_forecast():
    log_user_activity('Market Forecast')
    import random

    best_crop = None
    demand_level = None
    advice = None
    season = None
    region = None

    if request.method == 'POST':
        season = request.form.get('season')
        region = request.form.get('region')

        crops = {
            "Kharif": ["Rice", "Maize", "Soybean", "Cotton"],
            "Rabi": ["Wheat", "Barley", "Gram", "Mustard"],
            "Zaid": ["Cucumber", "Watermelon", "Moong", "Bajra"]
        }

        best_crop = random.choice(crops.get(season, ["Rice", "Wheat", "Maize"]))

        levels = ["Low", "Moderate", "High", "Very High"]
        demand_level = random.choice(levels)

        tips = [
            f"Focus on selling {best_crop} in local markets of {region}.",
            f"Consider contract farming for {best_crop}. Demand is {demand_level.lower()} this season.",
            f"High export potential for {best_crop} in nearby regions.",
            f"{best_crop} prices are stable; monitor wholesale trends weekly."
        ]
        advice = random.choice(tips)

        # -----------------------------
        #       SAVE TO DATABASE
        # -----------------------------
        try:
            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO market_forecast_usage
                (user_email, season, region, best_crop, demand_level, advice)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                session.get('email', 'guest'),
                season,
                region,
                best_crop,
                demand_level,
                advice
            ))
            mysql.connection.commit()
            cur.close()
        except Exception as e:
            print("Error saving market forecast usage:", e)

    return render_template(
        'market_forecast.html',
        best_crop=best_crop,
        demand_level=demand_level,
        advice=advice
    )

@app.route('/harvest-prediction', methods=['GET', 'POST'])
def harvest_prediction():
    log_user_activity('Harvest Prediction')
    from datetime import datetime, timedelta
    import random

    harvest_date = None
    duration = None
    advice = None
    crop_name = None
    sowing_date = None

    if request.method == 'POST':
        crop_name = request.form.get('crop_name')
        sowing_date_str = request.form.get('sowing_date')

        try:
            sowing_date = datetime.strptime(sowing_date_str, "%Y-%m-%d")
        except:
            sowing_date = datetime.now()

        crop_durations = {
            "wheat": 120,
            "rice": 110,
            "maize": 95,
            "soybean": 105,
            "cotton": 150,
            "sugarcane": 300
        }

        duration = crop_durations.get(crop_name.lower(), random.randint(90, 150))
        harvest_dt = sowing_date + timedelta(days=duration)
        harvest_date = harvest_dt.strftime("%Y-%m-%d")

        advices = [
            f"Plan your harvest around {harvest_date}. Avoid rainy periods.",
            f"{crop_name.title()} will be ready by {harvest_date}.",
            f"Monitor field & irrigation 2 weeks before {harvest_date}.",
            f"Best yield expected near {harvest_date}."
        ]
        advice = random.choice(advices)

        # SAVE TO DB
        try:
            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO harvest_prediction_usage
                (user_email, crop_name, sowing_date, harvest_date, duration_days, advice)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                session.get('email', 'guest'),
                crop_name,
                sowing_date.strftime("%Y-%m-%d"),
                harvest_date,
                duration,
                advice
            ))
            mysql.connection.commit()
            cur.close()
            print("✅ Data Saved Successfully!")

        except Exception as e:
            print("❌ DB Error:", e)

    return render_template(
        'harvest_prediction.html',
        harvest_date=harvest_date,
        duration=duration,
        advice=advice
    )

@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    log_user_activity('Chatbot')
    from flask import jsonify, request, render_template
    import random

    if request.method == 'GET':
        return render_template('chatbot.html')

    # POST request (chatbot AJAX response)
    data = request.get_json()
    user_choice = data.get('choice', '').lower()

    # Chatbot Logic
    if user_choice in ["start", "hi", "hello", "main"]:
        reply = random.choice([
            "👋 Namaskar! I'm your Smart Farming Assistant.",
            "🌾 Hello Farmer! How can I help your farm today?",
            "👩‍🌾 Ready to boost your crop productivity?"
        ])
        options = ["🌱 Crop Suggestion", "💧 Irrigation Help", "🌤️ Weather Update", "💰 Market Info", "🧪 Soil Tips"]

    elif user_choice == "🌱 crop suggestion":
        reply = random.choice([
            "Tell me your soil type, and I’ll suggest the best crops!",
            "Let's find the right crop for your land. What's your soil type?",
            "Okay! To recommend crops, please select your soil type 👇"
        ])
        options = ["Black Soil", "Red Soil", "Sandy Soil", "Clay Soil", "Back"]

    elif user_choice in ["black soil", "red soil", "sandy soil", "clay soil"]:
        crops = {
            "black soil": "Cotton, Soybean, and Wheat grow excellently in black soil.",
            "red soil": "Groundnut, Millets, and Pulses love red soil.",
            "sandy soil": "Best for Watermelon, Cucumber, and Potato.",
            "clay soil": "Ideal for Paddy, Sugarcane, and Maize."
        }
        reply = f"✅ For {user_choice.title()}, you can grow: \n{crops[user_choice]}"
        options = ["💧 Irrigation Help", "💰 Market Info", "Back"]

    elif user_choice == "💧 irrigation help":
        reply = random.choice([
            "💧 Use drip irrigation for water saving up to 40%.",
            "Sprinkle water in early morning or evening to avoid evaporation.",
            "Adjust irrigation schedule as per soil moisture readings."
        ])
        options = ["🌤️ Weather Update", "🏠 Main Menu"]

    elif user_choice == "🌤️ weather update":
        reply = random.choice([
            "☀️ This week: 30°C avg temperature, moderate rain chances.",
            "🌧️ Expect light showers in next 3 days. Avoid over-irrigation.",
            "🌤️ Dry spell expected, plan irrigation accordingly."
        ])
        options = ["💰 Market Info", "🏠 Main Menu"]

    elif user_choice == "💰 market info":
        reply = random.choice([
            "📊 Market Today:\n- Wheat ₹2300/q\n- Maize ₹1900/q\n- Cotton ₹6800/q",
            "💹 Current Rates:\nRice ₹3100/q, Soybean ₹4400/q",
            "📈 Crop Price Update:\nWheat rising, Soybean stable, Cotton moderate."
        ])
        options = ["🧪 Soil Tips", "🏠 Main Menu"]

    elif user_choice == "🧪 soil tips":
        reply = "🌱 Maintain pH between 6.5–7.5 for most crops.\nAdd organic compost and test soil yearly."
        options = ["🏠 Main Menu"]

    elif user_choice in ["back", "🏠 main menu"]:
        reply = "You're back to the main menu 👇"
        options = ["🌱 Crop Suggestion", "💧 Irrigation Help", "🌤️ Weather Update", "💰 Market Info", "🧪 Soil Tips"]

    else:
        reply = "🤖 Sorry, I didn’t get that. Choose an option below 👇"
        options = ["🏠 Main Menu"]

    # -----------------------------------------
    # ✅ INSERT INTO chatbot_usage (DB Logging)
    # -----------------------------------------
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO chatbot_usage 
            (user_email, user_choice, bot_reply)
            VALUES (%s, %s, %s)
        """, (session.get('email', 'guest'), user_choice, reply))

        mysql.connection.commit()
        cur.close()
    except Exception as e:
        print("DB Error:", e)

    return jsonify({"reply": reply, "options": options})












@app.route('/ecommerce-tools')
def ecommerce_tools():
    log_user_activity('ecommerce-tools')

    # Database Logging
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO ecommerce_tools_usage
            (user_email, platform_name, action)
            VALUES (%s, %s, %s)
        """, (session.get('email', 'guest'), "none", "page_view"))

        mysql.connection.commit()
        cur.close()
    except Exception as e:
        print("DB Error:", e)

    platforms = [
        {
            "name": "AgroStar",
            "description": "Buy quality agri-inputs, seeds, and fertilizers directly from trusted brands.",
            "image": url_for('static', filename='images/agrostar.jpg'),
            "link": "https://www.agrostar.in/"
        },
        {
            "name": "BigHaat",
            "description": "India’s leading online agri-store for farmers — shop seeds, fertilizers, and tools.",
            "image": url_for('static', filename='images/bighaat.jpg'),
            "link": "https://www.bighaat.com/"
        },
        {
            "name": "DeHaat",
            "description": "Comprehensive agri-service platform offering inputs, advisory, and market linkages.",
            "image": url_for('static', filename='images/deehat.png'),
            "link": "https://agrevolution.in/"
        },
        {
            "name": "KrishiHub",    
            "description": "Connects farmers with agri-buyers — ensures better pricing for your produce.",
            "image": url_for('static', filename='images/krishihub.jpg'),
            "link": "https://krishihub.com/"
        },
        {
            "name": "Amazon Kisan Store",
            "description": "Shop agricultural supplies directly from Amazon’s Kisan store.",
            "image": url_for('static', filename='images/amazonkisan.jpg'),
            "link": "https://www.amazon.in/b?node=2665398031"
        },
        {
            "name": "KisanKraft",
            "description": "Buy farm machinery and equipment directly from India’s trusted agri brand.",
            "image": url_for('static', filename='images/kisankraft.png'),
            "link": "https://www.kisankraft.com/"
        },
        {
            "name": "Tractor Junction",
            "description": "Compare tractors, prices, and dealers — make smart machinery decisions.",
            "image": url_for('static', filename='images/tractorjunction.png'),
            "link": "https://www.tractorjunction.com/"
        },
        {
            "name": "Nurture.Farm",
            "description": "End-to-end solutions for sustainable and profitable farming.",
            "image": url_for('static', filename='images/naturefarm.jpg'),
            "link": "https://nurture.farm/"
        },
    ]

    return render_template('ecommerce_tools.html', platforms=platforms)



# ---------------- Upload Config (optional) ----------------
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

from flask import Flask, render_template, jsonify
from flask_mysqldb import MySQL
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import random
import os



# ---------------- Upload Config ----------------
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ---------------- Create Prices Table ----------------
def create_prices_table():
    with app.app_context():
        cur = mysql.connection.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                id INT AUTO_INCREMENT PRIMARY KEY,
                crop_name VARCHAR(100),
                price VARCHAR(20),
                date_time DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        mysql.connection.commit()
        cur.close()

create_prices_table()

# ---------------- Price Update Function ----------------
# ---------------- Price Update Function ----------------
def update_prices():
    with app.app_context():
        try:
            cur = mysql.connection.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            prices = {
                "Tomato": f"₹{round(random.uniform(25, 35),1)}/kg",
                "Onion": f"₹{round(random.uniform(18, 26),1)}/kg",
                "Wheat": f"₹{round(random.uniform(17, 23),1)}/kg",
                "Sugarcane": f"₹{round(random.uniform(3.0, 4.5),1)}/kg",
                "Rice": f"₹{round(random.uniform(40, 55),1)}/kg",
                "Maize": f"₹{round(random.uniform(20, 28),1)}/kg"
            }

            for crop, price in prices.items():
                cur.execute(
                    "INSERT INTO prices (crop_name, price, date_time) VALUES (%s, %s, %s)",
                    (crop, price, now)
                )
            mysql.connection.commit()
            cur.close()
            print(f"✅ Prices updated at {now}")
        except Exception as e:
            print("❌ DB Error in update_prices():", e)


# ---------------- Scheduler Setup ----------------
scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(func=update_prices, trigger='interval', hours=1)
# DO NOT start scheduler here; start in main block


# ---------------- Home Route ----------------
@app.route('/')
def home():
    # Trigger price update if last record is not today
    cur = mysql.connection.cursor()
    cur.execute("SELECT date_time FROM prices ORDER BY id DESC LIMIT 1")
    last = cur.fetchone()
    cur.close()

    if not last or last[0].date() != datetime.now().date():
        update_prices()

    # Fetch today's prices
    cur = mysql.connection.cursor()
    cur.execute("SELECT crop_name, price FROM prices WHERE DATE(date_time) = CURDATE()")
    prices = {r[0]: r[1] for r in cur.fetchall()}
    cur.close()

    return render_template('index.html', prices=prices)

# ---------------- API Route ----------------
@app.route('/api/get_prices')
def api_get_prices():
    cur = mysql.connection.cursor()
    cur.execute("SELECT crop_name, price FROM prices WHERE DATE(date_time) = CURDATE()")
    prices = {r[0]: r[1] for r in cur.fetchall()}
    cur.close()
    return jsonify(prices)






from flask import Flask, render_template, jsonify, request
from flask_mysqldb import MySQL
from datetime import datetime


# Create farm_data table if not exists
def create_farm_data_table():
    cur = mysql.connection.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS farm_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            temperature FLOAT,
            humidity FLOAT,
            soil_moisture FLOAT,
            date_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    mysql.connection.commit()
    cur.close()

with app.app_context():
    create_farm_data_table()

@app.route('/api/save_farm_data', methods=['POST'])
def api_save_farm_data():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No JSON received"}), 400

    temp = data.get('temperature')
    hum = data.get('humidity')
    soil = data.get('soil_moisture')

    if temp is None or hum is None or soil is None:
        return jsonify({"status": "error", "message": "Incomplete data"}), 400

    try:
        cur = mysql.connection.cursor()
        now = datetime.now()

        # Insert new record every time (no hourly check)
        cur.execute("""
            INSERT INTO farm_data (temperature, humidity, soil_moisture, date_time)
            VALUES (%s, %s, %s, %s)
        """, (temp, hum, soil, now.strftime("%Y-%m-%d %H:%M:%S")))

        mysql.connection.commit()
        cur.close()
        return jsonify({"status": "success", "message": "Data saved successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/get_farm_data')
def api_get_farm_data():
    try:
        cur = mysql.connection.cursor()
        # fetch latest record
        cur.execute("""
            SELECT temperature, humidity, soil_moisture, date_time 
            FROM farm_data 
            ORDER BY date_time DESC 
            LIMIT 1
        """)
        row = cur.fetchone()
        cur.close()

        if row:
            return jsonify({
                "temperature": row[0],
                "humidity": row[1],
                "soil_moisture": row[2],
                "date_time": row[3].strftime("%Y-%m-%d %H:%M:%S")
            })
        else:
            return jsonify({"message": "No data found"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})




# -------------------------
# Custom datetime filter
# -------------------------
@app.template_filter('datetimeformat')
def datetimeformat(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M")
    return value

# -------------------------
# Fetch farm data by ID
# -------------------------
def get_farm_data_by_id(farm_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, temperature, humidity, soil_moisture, date_time FROM farm_data WHERE id=%s", (farm_id,))
    row = cur.fetchone()
    cur.close()
    if row:
        # Convert row to dictionary
        return {
            'id': row[0],
            'temperature': row[1],
            'humidity': row[2],
            'soil_moisture': row[3],
            'date_time': row[4]
        }
    return None

# -------------------------
# Update farm data
# -------------------------
def update_farm_data(farm_id, temperature, humidity, soil_moisture, date_time):
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE farm_data 
        SET temperature=%s, humidity=%s, soil_moisture=%s, date_time=%s 
        WHERE id=%s
    """, (temperature, humidity, soil_moisture, date_time, farm_id))
    mysql.connection.commit()
    cur.close()

# -------------------------
# Edit farm data route
# -------------------------
@app.route('/admin/edit_farm/<int:id>', methods=['GET', 'POST'])
def admin_edit_farm_data(id):
    # Authentication check
    if 'user' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    row = get_farm_data_by_id(id)
    if not row:
        return "Farm data not found", 404

    if request.method == 'POST':
        temperature = request.form['temperature']
        humidity = request.form['humidity']
        soil_moisture = request.form['soil_moisture']
        date_time = request.form['date_time']

        try:
            update_farm_data(id, temperature, humidity, soil_moisture, date_time)
            flash("Farm data updated successfully!", "success")
        except Exception as e:
            print(f"Error updating farm data: {e}")
            flash("Error updating farm data.", "danger")
        return redirect(url_for('admin_farm_insights'))

    return render_template('admin/edit_farm_data.html', row=row)

# -------------------------
# Delete farm data route
# -------------------------
@app.route('/admin/delete_farm_data/<int:id>', methods=['POST'])
def admin_delete_farm_data(id):
    if 'user' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM farm_data WHERE id=%s", (id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            flash("Farm data not found.", "warning")
            return redirect(url_for('admin_farm_insights'))

        cur.execute("DELETE FROM farm_data WHERE id=%s", (id,))
        mysql.connection.commit()
        cur.close()
        flash("Farm data deleted successfully!", "success")
    except Exception as e:
        print(f"Error deleting farm data: {e}")
        flash("Error deleting farm data.", "danger")

    return redirect(url_for('admin_farm_insights'))

# -------------------------
# Example admin insights route
# -------------------------
@app.route('/admin/farm_insights')
def admin_farm_insights():
    # Fetch all farm data
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, temperature, humidity, soil_moisture, date_time FROM farm_data")
    rows = cur.fetchall()
    cur.close()
    # Convert to list of dicts
    farm_data = [
        {
            'id': r[0],
            'temperature': r[1],
            'humidity': r[2],
            'soil_moisture': r[3],
            'date_time': r[4]
        } for r in rows
    ]
    return render_template('admin/farm_insights.html', farm_data=farm_data)




# ===================== Example index.html Loop =====================
"""
{% for crop, price in prices.items() %}
  <div class="crop-card">
    <h3>{{ crop }}</h3>
    <p>{{ price }}</p>
  </div>
{% endfor %}
"""

# =================================

def save_tool_usage(tool_name, input_data_dict, result_data_dict):
    """Saves any tool usage to the database."""
    import json
    user_email = session.get('email', 'guest')
    input_data = json.dumps(input_data_dict)
    result_data = json.dumps(result_data_dict)

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO tool_usage (user_email, tool_name, input_data, result_data)
        VALUES (%s, %s, %s, %s)
    """, (user_email, tool_name, input_data, result_data))
    mysql.connection.commit()
    cur.close()

# ========================================admin sidebar====================================
# ---------- Admin: List all registered users ----------
@app.route('/admin/all-users')
def admin_all_users():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, fullname, email, phone, address, password, profile_photo, role FROM users")
    users = cur.fetchall()
    cur.close()
    return render_template('admin/all_users.html', users=users)


@app.route('/admin/manage-users')
def admin_manage_users():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, fullname, email, phone, address, password, profile_photo, role FROM users")
    users = cur.fetchall()
    cur.close()
    return render_template('admin/manage_users.html', users=users)




@app.route('/admin/delete-user/<int:user_id>')
def admin_delete_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    mysql.connection.commit()
    cur.close()

    return redirect('/admin/manage-users')

@app.route('/admin/edit-user/<int:user_id>', methods=['GET', 'POST'])
def admin_edit_user(user_id):
    cur = mysql.connection.cursor()
    
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        address = request.form['address']
        role = request.form['role']

        profile_photo = None
        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and allowed_file(file.filename):
                filename = f"user_{user_id}_{file.filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                profile_photo = filename

        # Update query
        if profile_photo:
            cur.execute("""
                UPDATE users 
                SET fullname=%s, email=%s, password=%s, phone=%s, address=%s, role=%s, profile_photo=%s 
                WHERE id=%s
            """, (fullname, email, password, phone, address, role, profile_photo, user_id))
        else:
            cur.execute("""
                UPDATE users 
                SET fullname=%s, email=%s, password=%s, phone=%s, address=%s, role=%s
                WHERE id=%s
            """, (fullname, email, password, phone, address, role, user_id))

        mysql.connection.commit()
        cur.close()
        return redirect('/admin/manage-users')

    # GET request
    cur.execute("""
        SELECT id, fullname, email, password, phone, address, profile_photo, role 
        FROM users 
        WHERE id=%s
    """, (user_id,))
    user = cur.fetchone()
    cur.close()

    return render_template('admin/edit_user.html', user=user)


    # GET request → show form
    cur.execute("SELECT id, fullname, email, password, phone, address, profile_photo, role FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()
    cur.close()

    return render_template('admin/edit_user.html', user=user)

# ---------- Live Market Prices (view + delete) ----------




# ---------- Yield Predictions ----------


@app.route('/admin/yield_predictions')
def admin_yield_predictions():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, user_email, crop_name, soil_type, rainfall, temperature, humidity, fertilizer, predicted_yield, created_at FROM yield_prediction_usage ORDER BY created_at DESC")
        predictions = cur.fetchall()
        cur.close()
    except Exception as e:
        predictions = []
        print("Error fetching yield predictions:", e)
    
    return render_template('admin/yield_predictions.html', predictions=predictions)

# ---------- Disease Detection ----------
@app.route('/admin/disease_detections')
def admin_disease_detections():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page

    cur = mysql.connection.cursor()

    # Count total rows
    cur.execute("SELECT COUNT(*) FROM disease_detection_usage")
    total_rows = cur.fetchone()[0]

    # Fetch records
    cur.execute("""
        SELECT id, user_email, image, predicted_disease, remedy, created_at
        FROM disease_detection_usage
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """, (per_page, offset))

    rows = cur.fetchall()
    cur.close()

    total_pages = (total_rows + per_page - 1) // per_page

    return render_template(
        'admin/disease_detections.html',
        rows=rows,
        page=page,
        total_pages=total_pages,
        active_page='disease_detections'
    )



# ---------- Seed Quality Detection ----------
@app.route('/admin/seed_quality')
def admin_seed_quality():
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied. Admins only!", "danger")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            SELECT id, user_email, seed_type, sample_size, moisture, purity, image,
                   predicted_viability, recommendation, created_at
            FROM seed_quality_usage
            ORDER BY id DESC
            LIMIT 200
        """)
        rows = cur.fetchall()
    except Exception:
        rows = []
    cur.close()
    return render_template('admin/seed_quality.html', rows=rows, active_page='seed_quality')

# ---------- Rainfall Prediction ----------
@app.route('/admin/rainfall_predictions')
def admin_rainfall_predictions():
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied. Admins only!", "danger")
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT id, user_email, location, predicted_rainfall, message, created_at FROM rainfall_prediction_usage ORDER BY id DESC LIMIT 200")
        rows = cur.fetchall()
    except Exception:
        rows = []
    cur.close()
    return render_template('admin/rainfall_predictions.html', rows=rows, active_page='rainfall_predictions')


# ---------- Climate Advisory ----------
@app.route('/admin/climate_advisories')
def admin_climate_advisories():
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied. Admins only!", "danger")
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT id, user_email, temperature, humidity, rainfall, advisory, created_at FROM climate_advisory_usage ORDER BY id DESC LIMIT 200")
        rows = cur.fetchall()
    except Exception:
        rows = []
    cur.close()
    return render_template('admin/climate_advisories.html', rows=rows, active_page='climate_advisories')


# ---------- Mixed Crop Planning ----------
@app.route('/admin/mixed_crops')
def admin_mixed_crops():
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied. Admins only!", "danger")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            SELECT id, user_email, main_crop, compatible_crops, created_at 
            FROM mixed_crop_usage 
            ORDER BY id DESC 
            LIMIT 200
        """)
        rows = cur.fetchall()
    except Exception:
        rows = []
    cur.close()

    return render_template('admin/mixed_crops.html', rows=rows, active_page='mixed_crops')


# ---------- Water Requirement Forecasting ----------
@app.route('/admin/water_forecasts')
def admin_water_forecasts():
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied. Admins only!", "danger")
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT id, user_email, crop, water_need, advice, next_irrigation FROM water_forecast_usage ORDER BY id DESC LIMIT 200")
        rows = cur.fetchall()
    except Exception:
        rows = []
    cur.close()
    return render_template('admin/water_forecasts.html', rows=rows, active_page='water_forecasts')


# ---------- Market Demand Forecast ----------
@app.route('/admin/market_forecasts')
def admin_market_forecasts():
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied. Admins only!", "danger")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    try:
        # created_at field add केला
        cur.execute("""
            SELECT id, user_email, season, region, best_crop, demand_level, advice, created_at
            FROM market_forecast_usage
            ORDER BY id DESC
            LIMIT 200
        """)
        rows = cur.fetchall()
    except Exception:
        rows = []
    cur.close()

    return render_template('admin/market_forecasts.html', rows=rows, active_page='market_forecasts')
# ---------- Harvest Time Predictions ----------
@app.route('/admin/harvest_predictions')
def admin_harvest_predictions():
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied. Admins only!", "danger")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            SELECT id, user_email, crop_name, sowing_date, harvest_date, duration_days, advice, created_at
            FROM harvest_prediction_usage
            ORDER BY id DESC
            LIMIT 200
        """)
        rows = cur.fetchall()
    except Exception as e:
        print("Error fetching harvest predictions:", e)
        rows = []
    cur.close()

    return render_template('admin/harvest_predictions.html', rows=rows, active_page='harvest_predictions')

@app.route('/admin/edit_harvest_prediction/<int:id>', methods=['GET', 'POST'])
def admin_edit_harvest_prediction(id):
    cur = mysql.connection.cursor()
    
    if request.method == 'POST':
        crop = request.form['crop_name']
        sowing_date = request.form['sowing_date']
        harvest_date = request.form['harvest_date']
        duration = request.form['duration_days']
        advice = request.form['advice']

        cur.execute("""
            UPDATE harvest_prediction_usage
            SET crop_name=%s, sowing_date=%s, harvest_date=%s, duration_days=%s, advice=%s
            WHERE id=%s
        """, (crop, sowing_date, harvest_date, duration, advice, id))
        mysql.connection.commit()
        cur.close()
        flash("Harvest prediction updated successfully!", "success")
        return redirect(url_for('admin_harvest_predictions'))

    # GET method
    cur.execute("""
        SELECT id, user_email, crop_name, sowing_date, harvest_date, duration_days, advice, created_at
        FROM harvest_prediction_usage
        WHERE id=%s
    """, (id,))
    row = cur.fetchone()
    cur.close()

    if row:
        row = list(row)
        row[3] = row[3].strftime('%Y-%m-%d')  # sowing_date
        row[4] = row[4].strftime('%Y-%m-%d')  # harvest_date

    return render_template('admin/edit_harvest_prediction.html', row=row)


@app.route('/admin/delete_harvest_prediction/<int:id>', methods=['POST', 'GET'])
def admin_delete_harvest_prediction(id):
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied. Admins only!", "danger")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM harvest_prediction_usage WHERE id=%s", (id,))
    mysql.connection.commit()
    cur.close()
    flash("Harvest prediction deleted successfully!", "success")
    return redirect(url_for('admin_harvest_predictions'))

# ---------------- Chatbot Logs ----------------
@app.route('/admin/chatbot_logs')
def admin_chatbot_logs():
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied. Admins only!", "danger")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            SELECT id, user_email, user_choice, bot_reply, created_at
            FROM chatbot_usage
            ORDER BY id DESC
        """)
        rows = cur.fetchall()
    except Exception as e:
        print("DB Error:", e)
        rows = []
    cur.close()
    return render_template('admin/chatbot_logs.html', rows=rows, active_page='chatbot_logs')
@app.route('/admin/edit_chatbot/<int:id>', methods=['GET', 'POST'])
def admin_edit_chatbot(id):
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        user_choice = request.form['user_choice']
        bot_reply = request.form['bot_reply']
        cur.execute("UPDATE chatbot_usage SET user_choice=%s, bot_reply=%s WHERE id=%s",
                    (user_choice, bot_reply, id))
        mysql.connection.commit()
        cur.close()
        flash("Record updated successfully!", "success")
        return redirect(url_for('admin_chatbot_logs'))

    cur.execute("SELECT id, user_email, user_choice, bot_reply, created_at FROM chatbot_usage WHERE id=%s", (id,))
    row = cur.fetchone()
    cur.close()
    return render_template('admin/edit_chatbot_usage.html', row=row)


@app.route('/admin/delete_chatbot/<int:id>')
def admin_delete_chatbot(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM chatbot_usage WHERE id=%s", (id,))
    mysql.connection.commit()
    cur.close()
    flash("Record deleted successfully!", "success")
    return redirect(url_for('admin_chatbot_logs'))



# ---------- E-commerce tools (view platforms log) ----------
@app.route('/admin/ecommerce_tools')
def admin_ecommerce_tools():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, user_email, platform_name, action, created_at FROM ecommerce_tools_usage ORDER BY id DESC")
    rows = cur.fetchall()
    cur.close()
    return render_template('admin/ecommerce_tools.html', rows=rows, active_page='ecommerce_tools')

@app.route('/admin/edit_ecommerce_tool/<int:id>', methods=['GET', 'POST'])
def admin_edit_ecommerce_tools_usage(id):
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        platform_name = request.form['platform_name']
        action = request.form['action']
        cur.execute("UPDATE ecommerce_tools_usage SET platform_name=%s, action=%s WHERE id=%s",
                    (platform_name, action, id))
        mysql.connection.commit()
        cur.close()
        flash("Record updated successfully!", "success")
        return redirect(url_for('admin_ecommerce_tools'))

    cur.execute("SELECT id, user_email, platform_name, action, created_at FROM ecommerce_tools_usage WHERE id=%s", (id,))
    row = cur.fetchone()
    cur.close()
    return render_template('admin/edit_ecommerce_tools_usage.html', row=row)


@app.route('/admin/delete_ecommerce_tool/<int:id>')
def admin_delete_ecommerce_tools_usage(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM ecommerce_tools_usage WHERE id=%s", (id,))
    mysql.connection.commit()
    cur.close()
    flash("Record deleted successfully!", "success")
    return redirect(url_for('admin_ecommerce_tools'))

# ---------- Contact Us Data ----------
@app.route('/admin/contact_messages')
def admin_contact_messages():
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied. Admins only!", "danger")
        return redirect(url_for('login'))
    # We created Contact model via SQLAlchemy earlier; use SQLAlchemy or fallback to MySQL query
    try:
        # Using SQLAlchemy model Contact
        messages = Contact.query.order_by(Contact.created_at.desc()).all()
    except Exception:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, name, email, phone, message, created_at FROM contact ORDER BY id DESC LIMIT 500")
        messages = cur.fetchall()
        cur.close()
    return render_template('admin/contact_messages.html', messages=messages, active_page='contact_messages')

@app.route('/admin/live_prices')
def admin_live_prices():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, crop_name, price, date_time FROM prices ORDER BY date_time DESC LIMIT 20")
    prices = cur.fetchall()
    cur.close()
    return render_template('admin/live_prices.html', prices=prices, active_page='live_prices')

# Delete price
@app.route('/admin/delete-price/<int:price_id>')
def admin_delete_price(price_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM prices WHERE id=%s", (price_id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('admin_live_prices'))

# Edit price (GET + POST)
@app.route('/admin/edit-price/<int:price_id>', methods=['GET', 'POST'])
def admin_edit_price(price_id):
    cur = mysql.connection.cursor()
    
    if request.method == 'POST':
        crop_name = request.form['crop_name']
        price = request.form['price']
        cur.execute("UPDATE prices SET crop_name=%s, price=%s WHERE id=%s", (crop_name, price, price_id))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('admin_live_prices'))
    
    # GET request: fetch price details
    cur.execute("SELECT id, crop_name, price FROM prices WHERE id=%s", (price_id,))
    price_data = cur.fetchone()
    cur.close()
    return render_template('admin/edit_price.html', price=price_data)

@app.route('/admin/yield/delete/<int:id>')
def delete_yield_prediction(id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM yield_prediction_usage WHERE id=%s", (id,))
        mysql.connection.commit()
        cur.close()
        flash("Prediction deleted successfully!", "success")
    except:
        flash("Error deleting prediction", "danger")

    return redirect(url_for('admin_yield_predictions'))

@app.route('/admin/yield/edit/<int:id>', methods=['GET','POST'])
def edit_yield_prediction(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM yield_prediction_usage WHERE id=%s", (id,))
    data = cur.fetchone()

    if request.method == "POST":
        rainfall = request.form['rainfall']
        temperature = request.form['temperature']
        humidity = request.form['humidity']
        fertilizer = request.form['fertilizer']

        cur.execute("""
            UPDATE yield_prediction_usage 
            SET rainfall=%s, temperature=%s, humidity=%s, fertilizer=%s
            WHERE id=%s
        """, (rainfall, temperature, humidity, fertilizer, id))

        mysql.connection.commit()
        cur.close()

        flash("Prediction updated successfully!", "success")
        return redirect(url_for('admin_yield_predictions'))

    return render_template("admin/edit_yield_prediction.html", row=data)

@app.route('/admin/edit_detection/<int:id>', methods=['GET', 'POST'])
def edit_detection(id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, user_email, image, predicted_disease, remedy, created_at
        FROM disease_detection_usage
        WHERE id=%s
    """, (id,))
    row = cur.fetchone()
    cur.close()

    if not row:
        flash('Record not found', 'warning')
        return redirect(url_for('admin_disease_detections'))

    if request.method == 'POST':
        # Safely get form fields
        user_email = request.form.get('user_email')
        predicted_disease = request.form.get('predicted_disease')
        remedy = request.form.get('remedy')

        if not all([user_email, predicted_disease, remedy]):
            flash('All fields are required', 'danger')
            return redirect(request.url)

        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE disease_detection_usage
            SET user_email=%s, predicted_disease=%s, remedy=%s
            WHERE id=%s
        """, (user_email, predicted_disease, remedy, id))
        mysql.connection.commit()
        cur.close()

        flash('Record updated successfully', 'success')
        return redirect(url_for('admin_disease_detections'))

    return render_template('admin/edit_detection.html', row=row)


@app.route('/admin/delete_detection/<int:id>')
def delete_detection(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM disease_detection_usage WHERE id=%s", (id,))
    mysql.connection.commit()
    cur.close()

    return redirect(url_for('admin_disease_detections'))
# Edit Seed Quality Usage
@app.route('/admin/edit-seed-quality/<int:id>', methods=['GET', 'POST'])
def admin_edit_seed_quality_usage(id):
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied. Admins only!", "danger")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    if request.method == 'POST':
        seed_type = request.form['seed_type']
        sample_size = request.form['sample_size']
        moisture = request.form['moisture']
        purity = request.form['purity']
        predicted_viability = request.form['predicted_viability']
        recommendation = request.form['recommendation']

        cur.execute("""
            UPDATE seed_quality_usage
            SET seed_type=%s, sample_size=%s, moisture=%s, purity=%s, 
                predicted_viability=%s, recommendation=%s
            WHERE id=%s
        """, (seed_type, sample_size, moisture, purity, predicted_viability, recommendation, id))
        mysql.connection.commit()
        cur.close()
        flash("Seed quality record updated successfully!", "success")
        return redirect(url_for('admin_seed_quality'))

    cur.execute("SELECT * FROM seed_quality_usage WHERE id=%s", (id,))
    row = cur.fetchone()
    cur.close()
    return render_template('admin/edit_seed_quality.html', row=row)

# Delete Seed Quality Usage
@app.route('/admin/delete-seed-quality/<int:id>')
def admin_delete_seed_quality_usage(id):
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied. Admins only!", "danger")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM seed_quality_usage WHERE id=%s", (id,))
    mysql.connection.commit()
    cur.close()
    flash("Seed quality record deleted successfully!", "success")
    return redirect(url_for('admin_seed_quality'))

@app.route('/admin/edit-rainfall-prediction/<int:id>', methods=['GET', 'POST'])
def admin_edit_rainfall_prediction(id):
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied. Admins only!", "danger")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    
    if request.method == 'POST':
        predicted_rainfall = request.form.get('predicted_rainfall')
        message = request.form.get('message')

        try:
            cur.execute("""
                UPDATE rainfall_prediction_usage
                SET predicted_rainfall=%s, message=%s
                WHERE id=%s
            """, (predicted_rainfall, message, id))
            mysql.connection.commit()
            flash("Record updated successfully!", "success")
            return redirect(url_for('admin_rainfall_predictions'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error updating record: {str(e)}", "danger")
        finally:
            cur.close()
    
    # GET request: fetch record to show in form
    try:
        cur.execute("SELECT id, user_email, location, predicted_rainfall, message, created_at FROM rainfall_prediction_usage WHERE id = %s", (id,))
        row = cur.fetchone()
    except Exception:
        row = None
    finally:
        cur.close()
    
    if not row:
        flash("Record not found!", "danger")
        return redirect(url_for('admin_rainfall_predictions'))

    return render_template('admin/edit_rainfall_prediction.html', row=row)


@app.route('/admin/delete-rainfall-prediction/<int:id>', methods=['GET', 'POST'])
def admin_delete_rainfall_prediction(id):
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied. Admins only!", "danger")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM rainfall_prediction_usage WHERE id = %s", (id,))
        mysql.connection.commit()
        flash("Record deleted successfully!", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error deleting record: {str(e)}", "danger")
    finally:
        cur.close()
    
    return redirect(url_for('admin_rainfall_predictions'))

@app.route('/admin/edit_climate_advisory/<int:id>', methods=['GET', 'POST'])
def admin_edit_climate_advisory(id):
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied! Admin only.", "danger")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    if request.method == "POST":
        temperature = request.form['temperature']
        humidity = request.form['humidity']
        rainfall = request.form['rainfall']
        advisory = request.form['advisory']

        cur.execute("""
            UPDATE climate_advisory_usage 
            SET temperature=%s, humidity=%s, rainfall=%s, advisory=%s 
            WHERE id=%s
        """, (temperature, humidity, rainfall, advisory, id))

        mysql.connection.commit()
        cur.close()

        flash("Record updated successfully!", "success")
        return redirect(url_for('admin_climate_advisories'))

    cur.execute("SELECT id, user_email, temperature, humidity, rainfall, advisory FROM climate_advisory_usage WHERE id=%s", (id,))
    row = cur.fetchone()
    cur.close()

    return render_template('admin/edit_climate_advisory.html', row=row)

@app.route('/admin/delete_climate_advisory/<int:id>', methods=['POST', 'GET'])
def admin_delete_climate_advisory(id):
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied! Admin only.", "danger")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM climate_advisory_usage WHERE id=%s", (id,))
    mysql.connection.commit()
    cur.close()

    flash("Record deleted successfully!", "success")
    return redirect(url_for('admin_climate_advisories'))


# ---------- Edit Mixed Crop ----------
@app.route('/admin/edit-mixed-crop/<int:id>', methods=['GET', 'POST'])
def admin_edit_mixed_crop(id):
    if 'role' not in session or session['role'] != 'admin':
        flash("Access denied. Admin only!", "danger")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    if request.method == 'POST':
        main_crop = request.form['main_crop']
        compatible_crops = request.form['compatible_crops']

        cur.execute("""
            UPDATE mixed_crop_usage
            SET main_crop=%s, compatible_crops=%s
            WHERE id=%s
        """, (main_crop, compatible_crops, id))
        mysql.connection.commit()
        cur.close()
        flash("Record updated successfully!", "success")
        return redirect(url_for('admin_mixed_crops'))

    # GET request: fetch record
    cur.execute("SELECT id, user_email, main_crop, compatible_crops, created_at FROM mixed_crop_usage WHERE id=%s", (id,))
    row = cur.fetchone()
    cur.close()
    return render_template('admin/edit_mixed_crop.html', row=row)


# ---------- Delete Mixed Crop ----------
@app.route('/admin/delete-mixed-crop/<int:id>', methods=['POST','GET'])
def admin_delete_mixed_crop(id):
    if 'role' not in session or session['role'] != 'admin':
        flash("Access denied. Admin only!", "danger")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM mixed_crop_usage WHERE id=%s", (id,))
        mysql.connection.commit()
        flash("Record deleted successfully!", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error deleting record: {str(e)}", "danger")
    finally:
        cur.close()

    return redirect(url_for('admin_mixed_crops'))
@app.route('/admin/water_forecast/edit/<int:id>', methods=['GET', 'POST'])
def admin_edit_water_forecast(id):
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied. Admins only!", "danger")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    # GET request साठी record fetch करणे
    cur.execute("SELECT id, user_email, crop, water_need, advice, next_irrigation FROM water_forecast_usage WHERE id=%s", (id,))
    row = cur.fetchone()

    if request.method == 'POST':
        crop = request.form['crop']
        water_need = request.form['water_need']
        advice = request.form['advice']
        next_irrigation = request.form['next_irrigation']
        cur.execute("UPDATE water_forecast_usage SET crop=%s, water_need=%s, advice=%s, next_irrigation=%s WHERE id=%s",
                    (crop, water_need, advice, next_irrigation, id))
        mysql.connection.commit()
        flash("Record updated successfully!", "success")
        return redirect(url_for('admin_water_forecasts'))

    cur.close()
    return render_template('admin/edit_water_forecast.html', row=row)


@app.route('/admin/water_forecast/delete/<int:id>')
def admin_delete_water_forecast(id):
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied. Admins only!", "danger")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM water_forecast_usage WHERE id=%s", (id,))
    mysql.connection.commit()
    cur.close()
    flash("Record deleted successfully!", "success")
    return redirect(url_for('admin_water_forecasts'))


@app.route('/admin/delete_market_forecast/<int:id>')
def admin_delete_market_forecast(id):
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied. Admins only!", "danger")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM market_forecast_usage WHERE id=%s", (id,))
        mysql.connection.commit()
        flash("Record deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting record: {e}", "danger")
    cur.close()
    return redirect(url_for('admin_market_forecasts'))


@app.route('/admin/edit_market_forecast/<int:id>', methods=['GET', 'POST'])
def admin_edit_market_forecast(id):
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied. Admins only!", "danger")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    if request.method == 'POST':
        season = request.form['season']
        region = request.form['region']
        best_crop = request.form['best_crop']
        demand_level = request.form['demand_level']
        advice = request.form['advice']

        try:
            cur.execute("""
                UPDATE market_forecast_usage
                SET season=%s, region=%s, best_crop=%s, demand_level=%s, advice=%s
                WHERE id=%s
            """, (season, region, best_crop, demand_level, advice, id))
            mysql.connection.commit()
            flash("Record updated successfully.", "success")
        except Exception as e:
            flash(f"Error updating record: {e}", "danger")
        return redirect(url_for('admin_market_forecasts'))

    # GET request
    cur.execute("SELECT id, user_email, season, region, best_crop, demand_level, advice FROM market_forecast_usage WHERE id=%s", (id,))
    row = cur.fetchone()
    cur.close()
    return render_template('admin/edit_market_forecast.html', row=row)

@app.route('/admin/contact_messages/delete/<int:id>')
def admin_delete_contact_message(id):
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied!", "danger")
        return redirect(url_for('login'))

    try:
        Contact.query.filter_by(id=id).delete()
        db.session.commit()
    except:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM contact WHERE id=%s", (id,))
        mysql.connection.commit()
        cur.close()

    flash("Message deleted successfully!", "success")
    return redirect(url_for('admin_contact_messages'))

@app.route('/admin/contact_messages/edit/<int:id>', methods=['GET', 'POST'])
def admin_edit_contact_message(id):
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied!", "danger")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        message = request.form['message']

        cur.execute("""
            UPDATE contact
            SET name=%s, email=%s, phone=%s, message=%s
            WHERE id=%s
        """, (name, email, phone, message, id))

        mysql.connection.commit()
        cur.close()

        flash("Contact message updated successfully!", "success")
        return redirect(url_for('admin_contact_messages'))

    cur.execute(
        "SELECT id, name, email, phone, message FROM contact WHERE id=%s",
        (id,)
    )
    msg = cur.fetchone()
    cur.close()

    return render_template(
        'admin/edit_contact_message.html',
        msg=msg,
        active_page='contact_messages'
    )



# ===================== Run App =====================
if __name__ == '__main__':
    # Scheduler start here
    scheduler.start()  
    app.run(debug=True, use_reloader=True)
