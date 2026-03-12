from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector

app = Flask(__name__)
app.secret_key = "college_project_2026"

# ---------------- DATABASE CONNECTION ----------------
def get_db():
    try:
        return mysql.connector.connect(
            host="127.0.0.1",
            user="root",
            password="Charan@123",
            database="water_booking",
            autocommit=True
        )
    except Exception as e:
        print("Database Connection Error:", e)
        return None

# ---------------- ROUTES ----------------

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        db = get_db()
        if db:
            cursor = db.cursor()
            try:
                cursor.execute("INSERT INTO users (name, email, password, is_admin) VALUES (%s, %s, %s, 0)", 
                               (name, email, password))
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login'))
            except mysql.connector.Error as err:
                flash(f"Error: {err.msg}", "error")
            finally:
                db.close()
    return render_template('register.html')

@app.route('/admin/update-rate', methods=['POST'])
def update_rate():
    if 'user' not in session or session.get('is_admin') != 1:
        return redirect(url_for('login'))
        
    new_rate = request.form.get('rate')
    db = get_db()
    if db:
        cursor = db.cursor()
        cursor.execute("UPDATE settings SET water_rate_per_liter=%s WHERE id=1", (new_rate,))
        db.close()
        flash(f"Success! Water rate is now ₹{new_rate} per liter.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        db = get_db()
        if db:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))
            user = cursor.fetchone()
            db.close()
            if user:
                session.clear() 
                session['user'] = user['email']
                session['user_name'] = user['name']
                session['is_admin'] = user['is_admin']
                if user['is_admin'] == 1:
                    flash(f"Admin Logged In: {user['name']}", "success")
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('dashboard'))
            else:
                flash("Invalid Email or Password", "error")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    if session.get('is_admin') == 1: return redirect(url_for('admin_dashboard'))
    
    db = get_db()
    total_bookings = 0
    total_liters = 0
    if db:
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(quantity), 0) FROM bookings WHERE user_email=%s", (session['user'],))
        result = cursor.fetchone()
        total_bookings, total_liters = result
        db.close()
    return render_template('dashboard.html', name=session['user_name'], total_bookings=total_bookings, total_liters=total_liters)

@app.route('/admin-dashboard')
def admin_dashboard():
    if 'user' not in session or session.get('is_admin') != 1: return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("SELECT name, email, created_at FROM users WHERE is_admin = 0")
    all_users = cursor.fetchall()
    cursor.execute("SELECT b.*, u.name as customer_name FROM bookings b LEFT JOIN users u ON b.user_email = u.email ORDER BY b.id DESC")
    all_bookings = cursor.fetchall()
    cursor.execute("SELECT water_rate_per_liter FROM settings WHERE id=1")
    rate_row = cursor.fetchone()
    current_rate = rate_row['water_rate_per_liter'] if rate_row else 2.0
    
    db.close()
    return render_template('admin_dashboard.html', users=all_users, bookings=all_bookings, current_rate=current_rate)

@app.route('/book-water', methods=['GET', 'POST'])
def book_water():
    if 'user' not in session: 
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT water_rate_per_liter FROM settings WHERE id=1")
    rate_data = cursor.fetchone()
    rate = rate_data['water_rate_per_liter'] if rate_data else 2.0

    if request.method == 'POST':
        qty = request.form.get('quantity')
        date = request.form.get('booking_date')
        addr = request.form.get('address')
        pay_method = request.form.get('payment_method')
        total_amount = int(qty) * float(rate)

        cursor.execute("""
            INSERT INTO bookings (user_email, quantity, booking_date, address, amount, status, payment_method) 
            VALUES (%s, %s, %s, %s, %s, 'Pending', %s)
        """, (session['user'], qty, date, addr, total_amount, pay_method))
        db.close()

        if pay_method == 'Online':
            return render_template('payment_page.html', amount=total_amount)
        
        flash(f"Order for {qty}L confirmed! Total: ₹{total_amount}", "success")
        return redirect(url_for('view_bookings'))

    db.close()
    return render_template('book_water.html', rate=rate)

@app.route('/view-bookings')
def view_bookings():
    if 'user' not in session: return redirect(url_for('login'))
    db = get_db()
    if not db: return "Database Connection Error"
    
    cursor = db.cursor(dictionary=True) 
    cursor.execute("SELECT id, quantity, booking_date, address, amount, payment_method, status FROM bookings WHERE user_email=%s ORDER BY id DESC", (session['user'],))
    bookings = cursor.fetchall()
    db.close()
    return render_template('view_bookings.html', bookings=bookings)

@app.route('/approve-booking/<int:booking_id>')
def approve_booking(booking_id):
    if 'user' not in session or session.get('is_admin') != 1: 
        return redirect(url_for('login'))
    
    db = get_db()
    if db:
        cursor = db.cursor()
        cursor.execute("UPDATE bookings SET status='Approved' WHERE id=%s", (booking_id,))
        db.close()
        flash(f"Order #{booking_id} has been Approved!", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/update-status/<int:booking_id>')
def update_status(booking_id):
    if 'user' not in session or session.get('is_admin') != 1: return redirect(url_for('login'))
    db = get_db()
    if db:
        cursor = db.cursor()
        cursor.execute("UPDATE bookings SET status='Delivered' WHERE id=%s", (booking_id,))
        db.close()
        flash(f"Order #{booking_id} marked as Delivered!", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

# ---------------- STARTUP (KEEP THIS AT THE BOTTOM) ----------------
if __name__ == '__main__':
    with app.app_context():
        print("\n--- REGISTERED ROUTES ---")
        for rule in app.url_map.iter_rules():
            print(f"Endpoint: {rule.endpoint} | Route: {rule.rule}")
        print("-------------------------\n")
    
    app.run(debug=True)