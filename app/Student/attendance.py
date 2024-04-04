import datetime
#from datetime import datetime
from app.util.connection import DatabaseConnection
import face_recognition
import os
from flask import flash,redirect, url_for

def get_known_encoding(app):
    global known_faces, known_names
    # create two arrays store known faces encoding and their names
    known_faces = []
    known_names = []

    for filename in os.listdir('app/static/faces'):
        # image = face_recognition.load_image_file(os.path.join('static/faces', filename))
        image = face_recognition.load_image_file(os.path.join(app.root_path, 'static', 'faces'))
        encodings = face_recognition.face_encodings(image)#[0] if face_recognition.face_encodings(image) else None
        if encodings:
            encoding = encodings[0]
            known_faces.append(encoding)
            known_names.append(os.path.splitext(filename)[0])
    return known_faces, known_names

def check_attendance_already_marked(db, user_id,session_id,course_id, date):
    # Check if an attendance record exists for the given user_id, course_id, and date
    try:
        date_object = datetime.datetime.strptime(date, '%Y-%m-%d')
        formatted_date = date_object.strftime('%Y-%m-%d %H:%M:%S')

    except ValueError as e:
        flash(f"Error formatting date: {e}", 'error')
        return False

    query = "SELECT COUNT(*) FROM Attendance WHERE student_id = ? AND session_id = ? AND course_id=? AND attendance_date = ?"
    result = db.fetch_all(query, (user_id, session_id,course_id, formatted_date))
    if result:
        count = result[0][0]  # Assuming COUNT(*) returns a single row with a single column
        return count > 0
    return False

def markattendance_db(db, user_id, session_id,course_id, today,emotion):
    # Check if attendance for the given session has already been marked
    if check_attendance_already_marked(db, user_id, session_id,course_id, today):
        flash('Attendance already marked for today.', 'info')
        return 'already_marked'
        # return False

    # Assuming status determination logic is handled outside or simplified
    status = 'Present'
    try:
        # Insert the attendance record
        query_insert = """INSERT INTO Attendance (session_id, course_id, student_id, attendance_date, attendance_time, status, emotion) 
                                       VALUES (?, ?, ?,?, ?, ?, ?)"""
        attendance_time = datetime.datetime.now().strftime("%H:%M:%S")
        db.execute_query(query_insert, (session_id,course_id, user_id, today, attendance_time, status,emotion))
        db.commit()
    except Exception as e:
        print(f"Error inserting attendance record: {e}")
    return True
