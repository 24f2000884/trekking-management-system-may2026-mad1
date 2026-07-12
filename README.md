# Trekking Management Application

**MAD-I Project — May 2026 Term**

Student ID: `24f2000884`
Email: `24f2000884@ds.study.iitm.ac.in email`

## About

Trekking groups today coordinate through spreadsheets, phone calls and messaging apps, which makes it hard to approve treks, assign guides, track bookings, prevent overbooking, and keep a reliable trekking history.

TMA is a web application where three roles anmely **Admin**, **Trek Staff** and **Trekker** each log in to their own view of the same data, and cannot see or change anything outside their role.

- **Admin** creates and manages treks, adds and removes staff, assigns staff to treks, blacklists users, searches the system, and views all bookings.
- **Trek Staff** see only the treks assigned to them, update slots and status, and view the participant list.
- **Trekkers** browse and filter open treks, book a slot, cancel, and track their history.



## Tech stack

| Layer | Technology |
|---|---|
| Backend | Flask |
| ORM | Flask-SQLAlchemy |
| Database | SQLite |
| Templating | Jinja2 |
| Auth | Werkzeug Security (password hashing) + Flask session + `functools.wraps` role decorators |
| Frontend | Bootstrap 5 (CDN) |
| Charts | Chart.js 4 (CDN) |

## API

| Endpoint | Method | Description |
|---|---|---|
| `/api/treks` | GET | List all treks |
| `/api/treks/<id>` | GET | Single trek detail |
| `/api/treks/<id>` | PUT | Update a trek (admin only) |
| `/api/bookings` | POST | Book a trek |
| `/api/bookings/<id>` | DELETE | Cancel a booking |

Full specification in `api.yaml`.