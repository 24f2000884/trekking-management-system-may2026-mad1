from app import app, db
from models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    db.create_all()
    existing = User.query.filter_by(username='admin').first()
    if not existing:
        admin = User(
            username='admin',
            email='admin@trailhead.com',
            password_hash=generate_password_hash('admin123'),
            role='admin',
            is_active=True
        )
        db.session.add(admin)
        db.session.commit()
        print('Done. Admin created.')
    else:
        print('Already exists.')
