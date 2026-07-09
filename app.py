#app.py
from flask import Flask
from functools import wraps
from flask import session, redirect, url_for,flash, render_template, request
from werkzeug.security import generate_password_hash, check_password_hash
from models import db,User,Trek,Booking,StaffProfile,TrekStaffAssignment

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tma-mad1-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tma.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Warning !!!!, You are not logged in, Please log in first to continue.','warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_access_required(f):
    @wraps(f)
    def decorated(*args, **Kwargs):
        if session.get('role')!='admin':
            flash('Sorry, Access Denied, Only for Admins.','danger')
            return redirect(url_for('login'))
        return f(*args, **Kwargs)
    return decorated

def staff_access_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role')!= 'staff':
            flash('Staff only, Access Denied.','danger')
            return redirect(url_for('login'))
        return f(*args,**kwargs)
    return decorated

def trekker_access_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role')!= 'trekker':
            flash('Trekker only, Access Denied.','danger')
            return redirect(url_for('login'))
        return f(*args,**kwargs)
    return decorated


@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username= request.form['username'].strip()
        email= request.form['email'].strip()
        password= request.form['password']

        if User.query.filter_by(username=username).first():
            flash('OH,Username already Taken, Try something else.','danger')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('This email is already Registered, Please Login.','danger')
            return redirect(url_for('register'))
        
        user=User(username=username, email=email, password_hash=generate_password_hash(password),role='trekker')
        
        db.session.add(user)
        db.session.commit()

        flash('wohooo! Your Account has been created, Welcome to the world of trek. Please login to continue.','success')
        return redirect(url_for('login'))
    return render_template('auth/register.html')

@app.route('/login',methods= ['GET','POST'])
def login():
    if request.method=='POST':
        username= request.form['username'].strip()
        password= request.form['password']
        user=User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid Credentials, please check username or password.','danger')
            return redirect(url_for('login'))
        if user.is_blacklisted:
            flash('Your account has been deactivated, Please check.','danger')
            return redirect(url_for('login'))
        
        session['user_id']=user.id
        session['username']=user.username
        session['role']=user.role

        if user.role=='admin':
            return redirect(url_for('admin_dashboard'))
        elif user.role == 'staff':
            return redirect(url_for('staff_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))
    return render_template('auth/login.html')
    
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.','success')
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
@admin_access_required
def admin_dashboard():
    total_treks=Trek.query.count()
    total_users=User.query.filter_by(role='trekker').count()
    total_staff=User.query.filter_by(role='staff').count()
    total_bookings=Booking.query.count()
    recent_treks=Trek.query.order_by(Trek.created_at.desc()).limit(5).all()
    return render_template('admin/dashboard.html',total_treks=total_treks,total_users=total_users,total_staff=total_staff,total_bookings=total_bookings,recent_treks=recent_treks)

@app.route('/admin/treks')
@admin_access_required
def admin_treks():
    treks=Trek.query.all()
    return render_template('/admin/treks.html',treks=treks)

@app.route('/admin/trek/create', methods=['GET','POST'])
@admin_access_required
def create_trek():
    if request.method=='POST':
        from datetime import date
        t=Trek( 
            name=request.form['name'].strip(),
            location=request.form['location'].strip(),
            difficulty=request.form['difficulty'],
            duration_days=int(request.form['duration_days']),
            available_slots=int(request.form['slots']),
            total_slots=int(request.form['slots']),
            description=request.form.get('description', ''),
            status='Pending',
            start_date=date.fromisoformat(request.form['start_date']),
            end_date=date.fromisoformat(request.form['end_date']) 
        )

        db.session.add(t)
        db.session.commit()
        flash("Trek has been created Succesfully.",'success')
        return redirect(url_for('admin_treks'))
    return render_template('admin/create_trek.html')

@app.route('/admin/trek/edit/<int:trek_id>',methods=['GET','POST'])
@admin_access_required
def edit_trek(trek_id):
    t=Trek.query.get_or_404(trek_id)
    if request.method =="POST":
        t.name=request.form['name'].strip()
        t.location = request.form['location'].strip()
        t.difficulty = request.form['difficulty']
        t.available_slots = int(request.form['slots'])
        t.status = request.form['status']
        db.session.commit()
        flash('The trek has been updated successfully.','success')
        return redirect(url_for('admin_treks'))
    return render_template('/admin/edit_trek.html')

@app.route('/admin/trek/delete/<int:trek_id>',methods=['POST'])
@admin_access_required
def delete_trek(trek_id):
    t=Trek.query.get_or_404(trek_id)
    Booking.query.filter_by(trek_id=trek_id).delete()
    TrekStaffAssignment.query.filter_by(trek_id=trek_id).delete()  
    db.session.delete(t)      
    db.session.commit()
    flash('The trek has been deleted successfully.','success')
    return redirect(url_for('admin_treks'))


@app.route('/admin/staff')
@admin_access_required
def admin_staff():
    staff=User.query.filter_by(role='staff').all()
    return render_template('/admin/staff.html',staff=staff)

@app.route('/admin/staff/add',methods=['GET','POST'])
@admin_access_required
def add_staff():
    if request.method=='POST':
        user=User(
        username=request.form['username'].strip(),
        email=request.form['email'].strip(),
        password_hash=generate_password_hash(request.form['password']),
        role='staff')
        db.session.add(user)
        db.session.flush()
        profile=StaffProfile(user_id=user.id,name=request.form['name'].strip(),contact=request.form.get("contact",''))
        db.session.add(profile)
        db.session.commit()
        flash('Staff member added.','success')
        return redirect(url_for('admin_staff'))
    return render_template('/admin/add_staff.html')

@app.route('/admin/staff/assign/<int:trek_id>',methods=['GET','POST'])
@admin_access_required
def assign_staff(trek_id):
    trek=Trek.query.get_or_404(trek_id)
    all_staff=User.query.filter_by(role='staff',is_active=True).all()
    if request.method=='POST':
        staff_id=int(request.form['staff_id'])
        existing=TrekStaffAssignment.query.filter_by(trek_id=trek_id,staff_id=staff_id).first()
        if not existing:
            db.session.add(TrekStaffAssignment(trek_id=trek_id,staff_id=staff_id))
            db.session.commit()
            flash('Staff has been assigned to the trek.','success')
        return redirect(url_for('admin_treks'))
    return render_template('admin/assign_staff.html',trek=trek,staff=all_staff)

@app.route('/admin/users')
@admin_access_required
def admin_users():
    users=User.query.filter_by(role='trekker').all()
    return render_template('/admin/users.html',users=users)

@app.route('/admin/user/blacklist/<int:user_id>',methods=['POST'])
@admin_access_required
def blacklist_user(user_id):
    user=User.query.get_or_404(user_id)
    user.is_blacklisted= not user.is_backlisted
    db.session.commit()
    flash(f'Status has been updated for user {user.username}.','success')
    return redirect(url_for('admin_users'))

@app.route('/admin/search')
@admin_access_required
def admin_search():
    q = request.args.get('q', '').strip()
    treks = Trek.query.filter(Trek.name.ilike(f'%{q}%')).all() if q else []
    users = User.query.filter(User.username.ilike(f'%{q}%')).all() if q else []
    return render_template('admin/search.html', treks=treks, users=users,q=q)




if __name__ == '__main__':
    app.run(debug=True)
        
                              
                             