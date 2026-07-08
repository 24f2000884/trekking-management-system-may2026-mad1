#app.py
from flask import Flask
from functools import wraps
from flask import session, redirect, url_for,flash, render_template, request
from werkzeug.security import generate_password_hash, check_password_hash
from models import db,User

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
        if user.is_backlisted:
            flash('Your account has been deactivated, Please check.','danger')
            return redirect(url_for('login'))
        
        session['user_id']=user.id
        session['username']=user.username
        session['role']=user.role

        if user.role=='admin':
            return redirect(url_for('admin_dashboard'))
        elif user.role == 'staff':
            return redirect(url_for('staff dashboard'))
        else:
            return redirect(url_for('user dashboard'))
    return render_template('auth/login.html')
    
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.','success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
        
                              
                             