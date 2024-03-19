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

def check_attendance_already_marked(db, user_id,session_id, date):
    # Check if an attendance record exists for the given user_id, course_id, and date
    try:
        date_object = datetime.datetime.strptime(date, '%Y-%m-%d')
        formatted_date = date_object.strftime('%Y-%m-%d %H:%M:%S')

    except ValueError as e:
        flash(f"Error formatting date: {e}", 'error')
        return False

    query = "SELECT COUNT(*) FROM Attendance WHERE student_id = ? AND session_id = ? AND attendance_date = ?"
    result = db.fetch_all(query, (user_id, session_id, formatted_date))
    if result:
        count = result[0][0]  # Assuming COUNT(*) returns a single row with a single column
        return count > 0
    return False

# def markattendance_db(db, username, user_id,roll_no,course_id ,session_id,today):
#     # Convert 'today' to a datetime object to get the day name
#     today_date_object = datetime.datetime.strptime(today, '%d-%m-%Y')
#     today_date = today_date_object.strftime('%Y-%m-%d')
#     day_name = today_date_object.strftime('%A')  # Get the weekday name
#
#     # Fetch session_id, start time, and end time for the course session happening today
#     course_session_query = """
#        SELECT session_id, start_time, end_time
#        FROM CourseSessions
#        WHERE course_id = ? AND (day_of_week = ? OR session_date = ?)
#        """
#     session_result = db.fetch_all(course_session_query, (course_id, day_name,today_date))
#
#     if session_result:
#         session_id, start_time, end_time = session_result[0]
#         if check_attendance_already_marked(db, user_id, session_id, today):
#             flash('Attendance already marked for today.', 'info')
#             return False
#
#         current_time_str = datetime.datetime.now().strftime("%H:%M:%S")
#         current_time_obj = datetime.datetime.strptime(current_time_str, "%H:%M:%S").time()
#         status = 'Present' if start_time <= current_time_obj <= end_time else 'Late'
#
#
#
#
#         if isinstance(start_time, str):
#             start_time = datetime.datetime.strptime(start_time, "%H:%M:%S").time()
#         if isinstance(end_time, str):
#             end_time = datetime.datetime.strptime(end_time, "%H:%M:%S").time()
#
#         # Determine attendance status based on current time
#         if start_time <= current_time_obj <= end_time:
#             status = 'Present'
#         else:
#             status = 'Late'
#     else:
#         # Handle case where no results are returned, perhaps setting a default or logging an error
#         print(f"No course found with ID: {course_id}")
#         return
#
#     # Check if attendance for the user has already been marked today for the course
#     query_check = "SELECT * FROM Attendance WHERE username = ? AND date = ? AND course_id = ?"
#     if not db.fetch_all(query_check, (username, user_id, today_date, course_id)):
#         # Mark attendance for the user if not already marked
#         query_insert = """INSERT INTO Attendance (session_id, student_id, attendance_date, attendance_time, status) VALUES (?, ?, ?, ?, ?)"""
#
#         db.execute_query(query_insert,(session_id, user_id, today_date, datetime.datetime.now().strftime("%H:%M:%S"), status))
#         db.commit()
#         # flash('Attendance marked successfully.', 'success')
#         return True
#     return False
def markattendance_db(db, username, user_id, roll_no, course_id, session_id, today):
    # Check if attendance for the given session has already been marked
    if check_attendance_already_marked(db, user_id, session_id, today):
        flash('Attendance already marked for today.', 'info')
        return 'already_marked'
        # return False

    # Assuming status determination logic is handled outside or simplified
    status = 'Present'
    try:
        # Insert the attendance record
        query_insert = """INSERT INTO Attendance (session_id, student_id, attendance_date, attendance_time, status) 
                                       VALUES (?, ?, ?, ?, ?)"""
        attendance_time = datetime.datetime.now().strftime("%H:%M:%S")
        db.execute_query(query_insert, (session_id, user_id, today, attendance_time, status))
        db.commit()
    except Exception as e:
        print(f"Error inserting attendance record: {e}")
    return True
