from flask import Flask, request, jsonify, render_template, redirect, url_for
import json
import os
import random
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2

app = Flask(__name__)
DATA_FILE = 'sessions.json'
ASSIGNMENTS_FILE = 'assignments.json' # NEW FILE
ATTENDANCE_RADIUS_METERS = 50 

# --- Utility Functions ---

def _load_data():
    """Loads session data from a JSON file."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                for code, session in data.items():
                    if 'manual_attendance' not in session:
                        session['manual_attendance'] = []
                    if 'headcount' not in session:
                        session['headcount'] = 0
                return data
        except json.JSONDecodeError:
            return {}
    return {}

def _save_data(data):
    """Saves session data to a JSON file."""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def _load_assignments():
    """NEW: Loads assignments from a JSON file."""
    if os.path.exists(ASSIGNMENTS_FILE):
        try:
            with open(ASSIGNMENTS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def _save_assignments(data):
    """NEW: Saves assignments data to a JSON file."""
    with open(ASSIGNMENTS_FILE, 'w') as f:
        json.dump(data, f, indent=4)


def haversine_distance(lat1, lon1, lat2, lon2):
    # (Distance calculation function remains unchanged)
    R = 6371000 
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c

def get_client_ip_for_comparison(req):
    # (IP comparison function remains unchanged)
    ip_str = req.headers.get('X-Forwarded-For', req.remote_addr)
    ip_address = ip_str.split(',')[0].strip()

    if '.' in ip_address:
        return ip_address
    elif ':' in ip_address:
        return ":".join(ip_address.split(":")[:4])
    else:
        return ip_address

# --- Routing for Dashboard Pages (Jinja2 Templates) ---

@app.route('/')
def index():
    return redirect(url_for('dashboard_main')) 

@app.route('/dashboard')
def dashboard_main():
    return render_template('dashboard_main.html')

@app.route('/session')
def create_session_page():
    return render_template('create_session.html') 

@app.route('/student')
def student_page():
    return render_template('student.html') 

@app.route('/assignments')
def assignments_page(): # NEW PROFESSOR ROUTE
    """Renders the assignment creation and management page."""
    return render_template('assignments.html') 

# --- Placeholder Routes (Remains the same) ---
@app.route('/analytics')
def analytics_page():
    return render_template('simple_page.html', title="Analytics", content="Analytics features will be available soon.")

@app.route('/students')
def student_list_page():
    return render_template('simple_page.html', title="Student List", content="Manage your list of enrolled students here.")

@app.route('/network')
def network_status_page():
    return render_template('simple_page.html', title="Network Status", content="View and manage network configuration.")
    
@app.route('/security')
def security_page():
    return render_template('simple_page.html', title="Security", content="Security and user management settings.")

@app.route('/settings')
def settings_page():
    return render_template('simple_page.html', title="Settings", content="General application settings.")


# --- API Endpoints ---

@app.route('/api/create_session', methods=['POST'])
def create_session():
    # (Remains unchanged, but uses the updated _load_data/save_data)
    data = request.json
    course_name = data.get('course_name')
    
    try:
        professor_lat = float(data.get('latitude'))
        professor_lon = float(data.get('longitude'))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Invalid professor location data."}), 400
    
    if not course_name:
        return jsonify({"success": False, "message": "Missing course name."}), 400

    sessions = _load_data()
    session_code = str(random.randint(100000, 999999))
    hotspot_ip_key = get_client_ip_for_comparison(request) 
    
    sessions[session_code] = {
        "course_name": course_name,
        "professor_location": {"lat": professor_lat, "lon": professor_lon},
        "hotspot_ip_key": hotspot_ip_key,
        "attendance": [],
        "manual_attendance": [],
        "headcount": 0,
        "date": datetime.now().strftime("%Y-%m-%d")
    }
    _save_data(sessions)
    
    return jsonify({"success": True, "code": session_code, "hotspot_key": hotspot_ip_key})


@app.route('/api/add_assignment', methods=['POST'])
def add_assignment(): # NEW API FOR PROFESSOR
    data = request.json
    course_name = data.get('course_name')
    title = data.get('title')
    due_date_str = data.get('due_date')
    
    if not all([course_name, title, due_date_str]):
        return jsonify({"success": False, "message": "Missing assignment details."}), 400

    # Basic date validation
    try:
        datetime.strptime(due_date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({"success": False, "message": "Invalid date format. Must be YYYY-MM-DD."}), 400

    assignments = _load_assignments()
    assignments.append({
        "course": course_name,
        "title": title,
        "due_date": due_date_str,
        "timestamp": datetime.now().isoformat()
    })
    _save_assignments(assignments)

    return jsonify({"success": True, "message": "Assignment added successfully."})

@app.route('/api/get_assignments')
def get_assignments(): # NEW API FOR STUDENT
    """Returns all active assignments sorted by due date."""
    assignments = _load_assignments()
    
    # Sort assignments by due date
    assignments.sort(key=lambda x: x['due_date'])
    
    # Filter out assignments that are past due (optional, but good practice)
    today_str = datetime.now().strftime('%Y-%m-%d')
    active_assignments = [
        a for a in assignments if a['due_date'] >= today_str
    ]
    
    return jsonify({"assignments": active_assignments})


# (The remaining API routes: mark_attendance, manual_attendance, 
# update_headcount, and get_attendance remain unchanged)

# ... (rest of your existing code for attendance APIs) ...

@app.route('/api/mark_attendance', methods=['POST'])
def mark_attendance():
    # (Existing attendance logic)
    data = request.json
    student_id = data.get('student_id')
    session_code = data.get('session_code')
    
    try:
        student_lat = float(data.get('latitude'))
        student_lon = float(data.get('longitude'))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Invalid or missing location."}), 400

    if not all([student_id, session_code]):
        return jsonify({"success": False, "message": "Missing data."}), 400

    sessions = _load_data()
    session = sessions.get(session_code)
    
    if not session or session['date'] != datetime.now().strftime("%Y-%m-%d"):
        return jsonify({"success": False, "message": "Invalid or expired session code."}), 404

    if student_id in session['attendance'] or student_id in session['manual_attendance']:
        return jsonify({"success": False, "message": "Attendance already marked for this ID."}), 409
    
    # --- 1. Hotspot/IP Check (Robust) ---
    student_ip_key = get_client_ip_for_comparison(request)
    required_ip_key = session.get('hotspot_ip_key')
    
    if student_ip_key != required_ip_key:
        return jsonify({"success": False, "message": "Attendance requires connection to the professor's network."}), 403

    # --- 2. Geofencing Check (Location) ---
    prof_loc = session['professor_location']
    
    try:
        prof_lat = float(prof_loc['lat'])
        prof_lon = float(prof_loc['lon'])
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Internal error: Professor location data is invalid."}), 500

    distance = haversine_distance(prof_lat, prof_lon, student_lat, student_lon)
    
    if distance > ATTENDANCE_RADIUS_METERS:
        return jsonify({"success": False, "message": f"You are not within the attendance area (distance: {distance:.1f}m)."}), 403

    session['attendance'].append(student_id)
    _save_data(sessions)
    
    return jsonify({"success": True, "message": "Attendance marked successfully."})

@app.route('/api/manual_attendance', methods=['POST'])
def manual_attendance():
    # (Existing manual attendance logic)
    data = request.json
    student_id = data.get('student_id')
    session_code = data.get('session_code')

    if not all([student_id, session_code]):
        return jsonify({"success": False, "message": "Missing Student ID or Session Code."}), 400

    sessions = _load_data()
    session = sessions.get(session_code)
    
    if not session or session['date'] != datetime.now().strftime("%Y-%m-%d"):
        return jsonify({"success": False, "message": "Invalid or expired session code."}), 404
        
    if student_id in session['attendance'] or student_id in session['manual_attendance']:
        return jsonify({"success": False, "message": f"Student {student_id} is already marked present."}), 409

    session['manual_attendance'].append(student_id)
    _save_data(sessions)

    return jsonify({"success": True, "message": f"Student {student_id} manually marked present."})

@app.route('/api/update_headcount', methods=['POST'])
def update_headcount():
    # (Existing headcount update logic)
    data = request.json
    headcount = data.get('headcount')
    session_code = data.get('session_code')

    if session_code is None or headcount is None:
        return jsonify({"success": False, "message": "Missing data."}), 400

    try:
        headcount = int(headcount)
    except ValueError:
        return jsonify({"success": False, "message": "Headcount must be a number."}), 400

    sessions = _load_data()
    session = sessions.get(session_code)
    
    if not session or session['date'] != datetime.now().strftime("%Y-%m-%d"):
        return jsonify({"success": False, "message": "Invalid or expired session code."}), 404

    session['headcount'] = headcount
    _save_data(sessions)

    return jsonify({"success": True, "message": f"Headcount updated to {headcount}."})


@app.route('/api/get_attendance/<session_code>')
def get_attendance(session_code):
    # (Existing get attendance logic)
    sessions = _load_data()
    session = sessions.get(session_code)
    if session:
        total_attendance = session.get("attendance", []) + session.get("manual_attendance", [])
        headcount = session.get("headcount", 0)
        online_count = len(total_attendance)
        
        proxy_risk = 0
        if headcount > 0 and online_count > headcount:
            proxy_risk = online_count - headcount
            
        return jsonify({
            "course": session.get("course_name"),
            "headcount": headcount,
            "total_online_attendance": online_count,
            "proxy_risk": proxy_risk,
            "attendance_list": total_attendance,
            "hotspot_ip_key": session.get("hotspot_ip_key", "N/A")
        })
        
    return jsonify({"attendance_list": [], "message": "Session not found."}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
