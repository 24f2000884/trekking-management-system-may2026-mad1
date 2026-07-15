#app.py
from flask import Flask
from functools import wraps
from flask import session, redirect, url_for,flash, render_template, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from models import db,User,Trek,Booking,StaffProfile,TrekStaffAssignment
import json


app = Flask(__name__)
app.config['SECRET_KEY'] = 'tma-mad1-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tma.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

VALID_CYCLE={'Pending': ['Approved'],'Approved': ['Open','Pending'],'Open': ['Closed'],'Closed':['Completed'],'Completed': [],}

def can_transition(current,new):
    return new==current or new in VALID_CYCLE.get(current,[])

def complete_bookings_for(trek_id):
    Booking.query.filter_by(trek_id=trek_id,status='Booked').update({'status':'Completed'})

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
    def decorated(*args, **kwargs):
        if session.get('role')!='admin':
            flash('Sorry, Access Denied, Only for Admins.','danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
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
        confirm= request.form.get('confirm_password','')

        if not username or len(username)<3:
            flash("Username must be atleast 3 characters long.",'danger')
            return redirect(url_for('register'))
        if not email or '@' not in email:
            flash('Use a valid email address.','danger')
            return redirect(url_for('register'))
        if not password or len(password)<6:
            flash('Passwords must be atleast 6 characters long.','danger')
            return redirect(url_for('register'))
        if password != confirm:
            flash('The passwords do not match. Please re-enter them.','danger')
            return redirect(url_for('register'))

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
        if not user.is_active:
            flash('Your account is no longer active. Please contact the admin.','danger')
            return redirect(url_for('login'))
        
        session['user_id']=user.id
        session['username']=user.username
        session['role']=user.role

        if user.role=='admin':
            return redirect(url_for('admin_dashboard'))
        elif user.role == 'staff':
            return redirect(url_for('staff_dashboard'))
        else:
            return redirect(url_for('trekker_dashboard'))
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

    trek_names=[t.name for t in recent_treks]
    booking_counts=[Booking.query.filter_by(trek_id=t.id).count() for t in recent_treks]
    status_labels=['Pending','Approved','Open','Closed','Completed']
    status_counts=[Trek.query.filter_by(status=s).count() for s in status_labels]

    return render_template('admin/dashboard.html',total_treks=total_treks,total_users=total_users,total_staff=total_staff,total_bookings=total_bookings,recent_treks=recent_treks,trek_names=json.dumps(trek_names),booking_counts=json.dumps(booking_counts),status_labels=json.dumps(status_labels),status_counts=json.dumps(status_counts))

@app.route('/admin/treks')
@admin_access_required
def admin_treks():
    treks=Trek.query.all()
    next_statuses={t.id: VALID_CYCLE.get(t.status,[]) for t in treks}
    return render_template('/admin/treks.html',treks=treks,next_statuses=next_statuses)

@app.route('/admin/trek/create', methods=['GET','POST'])
@admin_access_required
def create_trek():
    if request.method=='POST':
        from datetime import date
        name=request.form['name'].strip()
        location=request.form['location'].strip()
        difficulty=request.form.get('difficulty','')
        duration=request.form.get('duration_days','')
        slots=request.form.get('slots','')
        start=request.form.get('start_date','')
        end=request.form.get('end_date','')        

        if not name:
            flash('Trek name is required','danger')
            return redirect(url_for('create_trek'))
        if not location:
            flash('Location of trek is required','danger')
            return redirect(url_for('create_trek'))
        if difficulty not in ['Easy','Moderate','Hard']:
            flash('Choose a valid Difficulty','danger')
            return redirect(url_for('create_trek'))
        if not duration.isdigit() or int(duration)<=0:
            flash('Duration of trek must be a valid number.','danger')
            return redirect(url_for('create_trek'))
        if not slots.isdigit() or int(slots)<=0:
            flash('Slots opened for trek must be a valid number.','danger')
            return redirect(url_for('create_trek'))
        
        try:
            start_date=date.fromisoformat(start)
            end_date=date.fromisoformat(end)
        except ValueError:
            flash('Enter a valid start and end date','danger')
            return redirect(url_for('create_trek'))
        if end_date<=start_date:
            flash('End date should be greater than start date.','danger')
            return redirect(url_for('create_trek'))

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
        name=request.form['name'].strip()
        location=request.form['location'].strip()
        difficulty=request.form.get('difficulty','')
        slots=request.form.get('slots','')
        status=request.form.get('status','')

        if not name:
            flash('Trek name is required.','danger')
            return redirect(url_for('edit_trek',trek_id=trek_id))
        if not location:
            flash('Location of trek is required','danger')
            return redirect(url_for('edit_trek',trek_id=trek_id))
        if difficulty not in ['Easy','Moderate','Hard']:
            flash('Choose a valid Difficulty.','danger')
            return redirect(url_for('edit_trek',trek_id=trek_id))
        if not slots.isdigit():
            flash('Slots opened for trek must be a valid number.','danger')
            return redirect(url_for('edit_trek',trek_id=trek_id))
        if int(slots) > t.total_slots:
            flash(f'Available slots cannot exceed the total slots available ({t.total_slots}).','danger')
            return redirect(url_for('edit_trek',trek_id=trek_id))
        if status not in ['Pending','Approved','Open','Closed','Completed']:
            flash('Choose a valid status for trek.','danger')
            return redirect(url_for('edit_trek',trek_id=trek_id))
        if not can_transition(t.status,status):
            flash(f'Invalid transition: a trek cannot move from {t.status} to {status}.','danger')
            return redirect(url_for('edit_trek',trek_id=trek_id))
 
        t.name=name
        t.location=location
        t.difficulty=difficulty
        t.available_slots=int(slots)
        t.status=status
        if t.status=='Completed':
            Booking.query.filter_by(trek_id=trek_id,status='Booked').update({'status':'Completed'})
            db.session.commit()
            flash("The trek has been marked completed successfully.",'success')
        db.session.commit()
        flash('The trek has been updated successfully.','success')
        return redirect(url_for('admin_treks'))
    allowed_statuses=[t.status]+VALID_CYCLE.get(t.status,[])
    return render_template('admin/edit_trek.html',trek=t,allowed_statuses=allowed_statuses)

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
    staff_treks={}
    for s in staff:
        trek_ids=[a.trek_id for a in TrekStaffAssignment.query.filter_by(staff_id=s.id).all()]
        staff_treks[s.id]=Trek.query.filter(Trek.id.in_(trek_ids)).all()
    return render_template('/admin/staff.html',staff=staff, staff_treks=staff_treks)

@app.route('/admin/staff/add',methods=['GET','POST'])
@admin_access_required
def add_staff():
    if request.method=='POST':
        username=request.form['username'].strip()
        email=request.form['email'].strip()
        password=request.form['password']
        name=request.form['name'].strip()

        if not username or len(username) < 3:
            flash('Username must be atleast 3 characters long.','danger')
            return redirect(url_for('add_staff'))
        if not email or '@' not in email:
            flash('Use a valid email address.','danger')
            return redirect(url_for('add_staff'))
        if not password or len(password) < 6:
            flash('Password must be at least 6 characters long.','danger')
            return redirect(url_for('add_staff'))
        if not name:
            flash('Staff name is required.','danger')
            return redirect(url_for('add_staff'))
        if User.query.filter_by(username=username).first():
            flash('OHO, Username already Taken, Try something else.','danger')
            return redirect(url_for('add_staff'))
        if User.query.filter_by(email=email).first():
            flash('This email is already Registered.Try another one','danger')
            return redirect(url_for('add_staff'))

        user=User(username=username, email=email, password_hash=generate_password_hash(password), role='staff')
        db.session.add(user)
        db.session.flush()
        profile=StaffProfile(user_id=user.id,name=name,contact=request.form.get("contact",''))
        db.session.add(profile)
        db.session.commit()
        flash('Staff member has been added Successfully.','success')
        return redirect(url_for('admin_staff'))
    return render_template('/admin/add_staff.html')

@app.route('/admin/staff/remove/<int:user_id>',methods=['POST'])
@admin_access_required
def remove_staff(user_id):
    user=User.query.get_or_404(user_id)
    if user.role!='staff':
        flash('This user is not a staff member.','danger')
        return redirect(url_for('admin_staff'))
    user.is_active=False
    TrekStaffAssignment.query.filter_by(staff_id=user_id).delete()
    if user.staff_profile:
        user.staff_profile.status='Inactive'
    db.session.commit()
    flash('Staff member has been deactivated and unassigned from all alloted treks.','success')
    return redirect(url_for('admin_staff'))

@app.route('/admin/staff/restore/<int:user_id>',methods=['POST'])
@admin_access_required
def restore_staff(user_id):
    user=User.query.get_or_404(user_id)
    if user.role!='staff':
        flash('This user is not a staff member.','danger')
        return redirect(url_for('admin_staff'))
    user.is_active=True
    if user.staff_profile:
        user.staff_profile.status='Active'
    db.session.commit()
    flash('Staff member has been reactivated.','success')
    return redirect(url_for('admin_staff'))

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
        else:
            flash('This staff member is already assigned to this trek.','warning')
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
    user.is_blacklisted= not user.is_blacklisted
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

@app.route('/admin/bookings')
@admin_access_required
def admin_bookings():
    bookings=Booking.query.order_by(Booking.booking_date.desc()).all()
    return render_template('admin/bookings.html', bookings=bookings)

@app.route('/admin/history')
@admin_access_required
def admin_history():
    bookings=Booking.query.order_by(Booking.booking_date.desc()).all()
    return render_template('admin/bookings.html', bookings=bookings)

@app.route('/staff/dashboard')
@staff_access_required
def staff_dashboard():
    staff_id=session['user_id']
    assignments=TrekStaffAssignment.query.filter_by(staff_id=staff_id).all()
    trek_ids=[assignment.trek_id for assignment in assignments]
    treks=Trek.query.filter(Trek.id.in_(trek_ids)).all()
    trek_counts={}
    for t in treks:
        trek_counts[t.id]=Booking.query.filter_by(trek_id=t.id).count()
    
    chart_labels=[t.name for t in treks]
    chart_counts=[trek_counts[t.id] for t in treks]

    return render_template('staff/staff_dashboard.html',treks=treks,trek_counts=trek_counts, chart_labels=json.dumps(chart_labels),chart_counts=json.dumps(chart_counts))

def is_staff_assigned(trek_id):
    return TrekStaffAssignment.query.filter_by(trek_id=trek_id,staff_id=session['user_id']).first() is not None

@app.route('/staff/trek/<int:trek_id>/update',methods=['GET','POST'])
@staff_access_required
def staff_update_trek(trek_id):
    if not is_staff_assigned(trek_id):
        flash('Warning:Access Denied, You are not assigned to this trek, KINDLY CHECK.','danger')
        return redirect(url_for('staff_dashboard'))
    trek=Trek.query.get_or_404(trek_id)
    allowed_statuses=[trek.status]+VALID_CYCLE.get(trek.status,[])
    if request.method=='POST':
        slots=request.form.get('slots','')
        status=request.form.get('status','')
        if not slots.isdigit():
            flash('Slots must be a Valid number.','danger')
            return redirect(url_for('staff_update_trek',trek_id=trek_id))
        if int(slots) > trek.total_slots:
            flash(f'Available slots cannot exceed the total slots ({trek.total_slots}).','danger')
            return redirect(url_for('staff_update_trek',trek_id=trek_id))
        if status not in ['Pending','Approved','Open','Closed','Completed']:
            flash('Choose a valid status for trek.','danger')
            return redirect(url_for('staff_update_trek',trek_id=trek_id))
        if not can_transition(trek.status,status):
            flash(f'Invalid transition: a trek cannot move from {trek.status} to {status}.','danger')
            return redirect(url_for('staff_update_trek',trek_id=trek_id))
        
        trek.available_slots=int(slots)
        trek.status=status
        if status=='Completed':
            complete_bookings_for(trek_id)
        db.session.commit()
        flash('Trek status has been updated Successfully.','success')
        return redirect(url_for('staff_dashboard'))
    return render_template('staff/update_trek.html',trek=trek,allowed_statuses=allowed_statuses)

@app.route('/staff/trek/<int:trek_id>/trekkers')
@staff_access_required
def staff_trekkers(trek_id):
    if not is_staff_assigned(trek_id):
        flash('Warning:Access Denied, You are not assigned to this trek, KINDLY CHECK.','danger')
        return redirect(url_for('staff_dashboard'))
    trek=Trek.query.get_or_404(trek_id)
    trekkers=Booking.query.filter_by(trek_id=trek_id).all()
    return render_template('staff/trekkers.html',trek=trek,trekkers=trekkers)

@app.route('/staff/trek/<int:trek_id>/history')
@staff_access_required
def staff_trek_history(trek_id):
    if not is_staff_assigned(trek_id):
        flash('Warning:Access Denied, You are not assigned to this trek, KINDLY CHECK.','danger')
        return redirect(url_for('staff_dashboard'))
    trek=Trek.query.get_or_404(trek_id)
    trekkers=Booking.query.filter_by(trek_id=trek_id).order_by(Booking.booking_date.desc()).all()
    return render_template('staff/trekkers.html',trek=trek,trekkers=trekkers)

@app.route('/trekker/dashboard')
@trekker_access_required
def trekker_dashboard():
    user_id= session['user_id']
    open_treks=Trek.query.filter_by(status='Open').all()
    my_bookings=Booking.query.filter_by(user_id=user_id).all()
    history_labels=['Booked','Completed','Cancelled']
    history_counts=[Booking.query.filter_by(user_id=user_id,status=s).count() for s in history_labels]
    return render_template('trekker/trekker_dashboard.html', open_treks=open_treks, my_bookings=my_bookings, history_labels=json.dumps(history_labels),history_counts=json.dumps(history_counts))

@app.route('/trekker/profile/edit',methods=['GET','POST'])
@trekker_access_required
def edit_profile():
    user=User.query.get_or_404(session['user_id'])
    if request.method=='POST':
        username=request.form['username'].strip()
        email=request.form['email'].strip()
        contact=request.form.get('contact','').strip()

        if User.query.filter(User.username ==username,User.id!=user.id).first():
            flash('Sorry, This Username is taken, try something else.','danger')
            return redirect(url_for('edit_profile'))
        
        if User.query.filter(User.email==email,User.id!=user.id).first():
            flash("Sorry, this email is already registered, use another email or sign in.",'danger')
            return redirect(url_for('edit_profile'))
        
        user.username= username
        user.email=email
        user.contact=contact
        db.session.commit()
        session['username']=user.username
        flash('Your has been successfully updated. Book your new adventure','success')
        return redirect(url_for('trekker_dashboard'))
    return render_template('trekker/profile.html',user=user)
       

@app.route('/trekker/treks')
@trekker_access_required
def trekker_treks():
    q=request.args.get('q','').strip()
    difficulty=request.args.get('difficulty','')
    location=request.args.get('location','')
    query=Trek.query.filter_by(status='Open')
    if q:
        query=query.filter(Trek.name.ilike(f'%{q}%'))
    if difficulty:
        query=query.filter_by(difficulty=difficulty)
    if location:
        query=query.filter(Trek.location.ilike(f'%{location}%'))
    
    treks=query.all()
    return render_template('trekker/treks.html',treks=treks,q=q,difficulty=difficulty, location=location)

@app.route('/trekker/trek/<int:trek_id>/book',methods=['POST'])
@trekker_access_required
def book_trek(trek_id):
    user_id=session['user_id']
    trek=Trek.query.get_or_404(trek_id)
    if trek.status!='Open':
        flash("Sorry, This trek hasn't opened yet. Check later or contact admin.",'danger')
        return redirect(url_for('trekker_treks'))
    if trek.available_slots<=0:
        flash("Sorry, this trek is full,Try next time.",'danger')
        return redirect(url_for('trekker_treks'))
    existing=Booking.query.filter_by(user_id=user_id,trek_id=trek_id,status='Booked').first()
    if existing:
        flash("You already have an active booking for this trek.",'warning')
        return redirect(url_for('trekker_treks'))
    
    try:
        booking=Booking(user_id=user_id,trek_id=trek_id)
        db.session.add(booking)
        trek.available_slots-=1
        db.session.commit()
        flash(f"WOOHOO!!, Your Booking for {trek.name} is successful.",'success')
    except Exception:
        db.session.rollback()
        flash("Error Occured,Try again later.",'danger')

    return redirect(url_for('trekker_bookings'))

@app.route('/trekker/bookings')
@trekker_access_required
def trekker_bookings():
    bookings=Booking.query.filter_by(user_id=session['user_id']).all()
    return render_template('trekker/bookings.html',bookings=bookings)


@app.route('/trekker/trek/<int:trek_id>/cancel',methods=['POST'])
@trekker_access_required
def cancel_booking(trek_id):
    booking=Booking.query.filter_by(user_id=session['user_id'],trek_id=trek_id, status='Booked').first_or_404()
    booking.status='Cancelled'
    booking.trek.available_slots+=1
    db.session.commit()
    flash('Your Booking has been cancelled.','success')
    return redirect(url_for('trekker_bookings'))

@app.route('/trekker/history')
@trekker_access_required
def trekker_history():
    history=Booking.query.filter(Booking.user_id==session['user_id'],Booking.status.in_(['Completed','Cancelled'])).order_by(Booking.booking_date.desc()).all()
    return render_template('/trekker/history.html', history=history)


@app.route('/admin/trek/<int:trek_id>/status',methods=['POST'])
@admin_access_required
def update_trek_status(trek_id):
    trek=Trek.query.get_or_404(trek_id)
    new_status=request.form['status']
    if new_status not in VALID_CYCLE.get(trek.status,[]):
        flash(f'You cannot move forward from {trek.status} to {new_status}.','danger')
        return redirect(url_for('admin_treks'))
    trek.status=new_status
    if new_status=='Completed':
        Booking.query.filter_by(trek_id=trek_id,status='Booked').update({'status':'Completed'})
    db.session.commit()
    flash(f'Trek status has been updated to {new_status}.','success')
    return redirect(url_for('admin_treks'))







@app.route('/api/treks',methods=['GET'])
def api_treks():
    treks=Trek.query.all()
    return jsonify(
        [{'id':t.id,'name':t.name,'location':t.location, 'difficulty':t.difficulty,'status':t.status, 'available_slots':t.available_slots,'total_slots':t.total_slots, 'start_date':t.start_date.isoformat() if t.start_date else None, 'end_date':t.end_date.isoformat() if t.end_date else None,}
        for t in treks]
        ),200
 
@app.route('/api/treks/<int:trek_id>',methods=['GET'])
def api_trek_detail(trek_id):
    t=Trek.query.get(trek_id)
    if not t:
        return jsonify({'error':'Trek not found.'}),404
    return jsonify({'id':t.id,'name':t.name,'location':t.location,'difficulty':t.difficulty,'duration_days':t.duration_days,'status':t.status,'available_slots':t.available_slots,'total_slots':t.total_slots,'description':t.description,'start_date':t.start_date.isoformat() if t.start_date else None,'end_date':t.end_date.isoformat() if t.end_date else None,}),200

@app.route('/api/treks/<int:trek_id>',methods=['PUT'])
def api_update_trek(trek_id):
    if session.get('role')!='admin':
        return jsonify({'error':'Admin access required.'}),401
    trek=Trek.query.get(trek_id)
    if not trek:
        return jsonify({'error':'Trek not found.'}),404
    data=request.get_json(silent=True) or {}
    if 'name' in data:
        if not str(data['name']).strip():
            return jsonify({'error':'Name cannot be empty.'}),400
        trek.name=str(data['name']).strip()
    if 'location' in data:
        trek.location=str(data['location']).strip()
    if 'difficulty' in data:
        if data['difficulty'] not in ['Easy','Moderate','Hard']:
            return jsonify({'error':'Invalid difficulty.'}),400
        trek.difficulty=data['difficulty']
    if 'available_slots' in data:
        if not isinstance(data['available_slots'],int) or data['available_slots']<0:
            return jsonify({'error':'Available_slots must be a valid number.'}),400
        trek.available_slots=data['available_slots']
    if 'status' in data:
        if data['status'] not in ['Pending','Approved','Open','Closed','Completed']:
            return jsonify({'error':'Invalid status.'}),400
        if not can_transition(trek.status,data['status']):
            return jsonify({'error':f"Invalid transition from {trek.status} to {data['status']}."}),400
        trek.status=data['status']
        if data['status']=='Completed':
            complete_bookings_for(trek_id)
    db.session.commit()
    return jsonify({'id':trek.id,'name':trek.name,'status':trek.status,'available_slots':trek.available_slots,'message':'Updated'}),200

@app.route('/api/bookings',methods=['POST'])
def api_create_booking():
    if 'user_id' not in session:
        return jsonify({'error':'Login is required.'}),401
    data=request.get_json(silent=True) or {}
    try:
        trek_id=int(data.get('trek_id'))
    except (TypeError,ValueError):
        return jsonify({'error':'A valid trek_id is required.'}),400
    trek=Trek.query.get(trek_id)
    if not trek:
        return jsonify({'error':'Trek not found.'}),404
    if trek.status!='Open':
        return jsonify({'error':'Trek is not open for booking yet.'}),400
    if trek.available_slots<=0:
        return jsonify({'error':'Trek is full. Try next time'}),400
    if Booking.query.filter_by(user_id=session['user_id'],trek_id=trek_id,status='Booked').first():
        return jsonify({'error':'You already have an active booking for this trek.'}),400
    booking=Booking(user_id=session['user_id'],trek_id=trek_id)
    db.session.add(booking)
    trek.available_slots-=1
    db.session.commit()
    return jsonify({'id':booking.id,'user_id':booking.user_id,'trek_id':booking.trek_id,'status':booking.status,'message':'Booked'}),201
 
 
@app.route('/api/bookings/<int:booking_id>',methods=['DELETE'])
def api_cancel_booking(booking_id):
    if 'user_id' not in session:
        return jsonify({'error':'Login is required.'}),401
    if session.get('role')=='admin':
        booking=Booking.query.get(booking_id)
    else:
        booking=Booking.query.filter_by(id=booking_id,user_id=session['user_id']).first()
    if not booking:
        return jsonify({'error': 'Booking not found.'}),404
    if booking.status!='Cancelled':
        booking.status='Cancelled'
        booking.trek.available_slots+=1
        db.session.commit()
    return jsonify({'id':booking.id,'status':booking.status,'message':'Cancelled'}),200
 
if __name__ == '__main__':
    app.run(debug=True)
