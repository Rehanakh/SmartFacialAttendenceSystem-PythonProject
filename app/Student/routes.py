import pickle
import numpy as np
from flask import Flask,Blueprint, current_app, render_template, request, flash, redirect, url_for, jsonify,Response,session
from .services import fetch_user_details,fetch_user_image_path,register_user ,known_faces,known_names,update_encodings,is_face_unique,capture_image_from_webcam
from .attendance import markattendance_db
from app.util.connection import DatabaseConnection
import face_recognition
import datetime
import os
import time
import shutil
from .models import CourseSession
from sqlalchemy import or_
import cv2
import logging
logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s:%(levelname)s:%(message)s')
#print("key",os.urandom(24))

today= datetime.date.today().strftime("%Y_%m_%d").replace("_","-")
db = DatabaseConnection()

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')


def student_setup_routes(app):
    @app.route('/')
    def home():
        # return 'Hello, World!'
        return render_template('home.html')

    known_faces, known_names = [], []

    def load_known_faces():
        known_faces_dir =  r"C:\Users\Rehana\Desktop\Big_Data_Semester1\Programming_for_big-data\Project\FacialRecognitionAttendanceSystem\app\static\faces"
        for filename in os.listdir(known_faces_dir):
            name, _ = os.path.splitext(filename)
            image_path = os.path.join(known_faces_dir, filename)
            image = face_recognition.load_image_file(image_path)
            encoding = face_recognition.face_encodings(image)[0]
            known_faces.append(encoding)
            known_names.append(name)
        print("Loaded known faces.")

    load_known_faces()

    @app.route('/registration', methods=['GET', 'POST'])
    def registration():
        if request.method == 'POST':
            userType = request.form.get('userType', 'defaultType')  # Added defaultType as a fallback
            status = request.form.get('status', 'pending')
            username = request.form['newusername']
            roll_no = request.form['newrollno']
            email = request.form['email']
            full_name = request.form['fullname']
            password = request.form['password']
            confirm_password = request.form['confirm_password']

            # Prepare data to send back to the form in case of re-rendering
            session['form_data'] = {'username': username, 'email': email, 'fullname': full_name, 'roll_no': roll_no}
            form_data = session.get('form_data', {})

            if password != confirm_password:
                flash('Passwords do not match. Please try again.', 'error')
                return render_template('registration.html', form_data=session.pop('form_data', {}))

            # Step 1: Capture the image from the webcam
            captured_image_path=capture_image_from_webcam(username, roll_no)
            if not captured_image_path or not os.path.exists(captured_image_path):
                flash("Failed to capture image. Please try again.", "error")
                return render_template('registration.html')

            try:
                new_user_image = face_recognition.load_image_file(captured_image_path)
                new_user_encoding = face_recognition.face_encodings(new_user_image)[0]

                # Step 2: Check if the face is unique
                if not is_face_unique(new_user_encoding):
                    flash('A similar face has already been registered.', 'error')
                    os.remove(captured_image_path)
                    return render_template('registration.html')
            except IndexError:
                flash("No face detected in the image. Please try again.", "error")
                if os.path.exists(captured_image_path):
                    os.remove(captured_image_path)
                return render_template('registration.html')

            # if is_face_unique(new_user_encoding):
                #write below in regiter_user()
                # img_name = f"{username}_{roll_no}.jpg"
                # permanent_image_path = os.path.join(current_app.root_path, 'app', 'static', 'faces', img_name)
                #
                # # Save the captured image to the permanent path
                # with open(permanent_image_path, "wb") as img_file:
                #     img_file.write(captured_image.getbuffer())  # Assuming 'captured_image' supports this operation

            # Construct the permanent image path
            img_name = f"{username}_{roll_no}.jpg"
            permanent_image_path = os.path.join(current_app.root_path, 'app', 'static', 'faces', img_name)

            # Move the image from the temporary path to the permanent path
            shutil.move(captured_image_path, permanent_image_path)

            # Step 3 & 4: Proceed with registration since the face is unique

            if register_user(userType, status, username, roll_no, email, full_name, password, permanent_image_path):

                # Step 5: Update encodings
                update_encodings()  # Update encoding file with new user's encoding
                flash('Registration Successful!', 'success')
            else:
                flash('Registration Failed! Please try again.', 'error')

            if os.path.exists(captured_image_path):
                os.remove(captured_image_path)
            return redirect(url_for('registration'))

        return render_template('registration.html')

    @app.route('/Studentdashboard')
    def Studentdashboard():
        if 'username' not in session:
            # Redirect to login page if user is not logged in
            return redirect(url_for('login'))
        return render_template('Studentdashboard.html')
        pass

    @app.route('/studentlogin', methods=['GET', 'POST'])
    def studentlogin():      #For Student Login redirect to StudentLogin Page
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            # Validate login credentials (this is a placeholder, implement your validation logic)
            return redirect('/markattendance')  # Redirect to the attendance marking page
        return render_template('studentlogin.html')
        pass

    @app.route('/home', methods=['GET'], endpoint='home_endpoint')
    def home():
        # Assuming 'home.html' is the name of your HTML file with the navbar
        return render_template('home.html')
        pass

    @app.route('/')
    def index():
        return redirect(url_for('home'))
        pass

    @app.route('/login', methods=['GET', 'POST'])
    def login():     #To Login Student after putting credentials on Student Login page
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']

            # Fetch user details from the database
            user = fetch_user_details(username)

            if user and user.PasswordHash == password:
                session['user_id'] = user.UserId
                session['username'] = user.Username
                session['roll_no'] = user.RollNumber
                session.permanent = True
                #change:03-03-2024
                return redirect(url_for('Studentdashboard') + '?login_success=1')

            else:
                # If the user was not found, flash an error message
                flash('Login failed. User not found.', 'error')

            # Display the login page with or without the login_success flag
        return render_template('Studentlogin.html', login_success=request.args.get('login_success', '0'))
        pass

    @app.route('/logout')
    def logout():
        logging.debug('Logging out user.')
        # Clear the session
        session.clear()
        # flash('You have been logged out.', 'success')
        return redirect(url_for('home'))
        pass
    @app.route('/StudentUpdateProfile', methods=['GET', 'POST'])
    def StudentUpdateProfile():
        if 'username' not in session:
            flash('Please log in to view this page.', 'error')
            return redirect(url_for('studentlogin'))

        username = session['username']
        user_details = fetch_user_details(username)

        if request.method == 'POST':
            email = request.form.get('email')
            full_name = request.form.get('full_name')
            roll_number = request.form.get('roll_number')
            user_id = session['user_id']
            new_username = request.form['Username']

            existing_user = db.fetch_all("SELECT * FROM Users WHERE username = ? AND UserType = 'S'", (new_username,))
            if existing_user:
                flash('Username already exists. Choose a different one.', 'error')
                return redirect(url_for('StudentProfileUpdate'))

            # Construct the SQL query to update user details
            query = "UPDATE users SET Username=?, Email=?, FullName=?, RollNumber=? WHERE UserId = ?"
            db.execute_query(query, (new_username, email, full_name, roll_number, user_id))
            session['username'] = new_username
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('StudentUpdateProfile'))

        return render_template('StudentUpdateProfile.html', user=user_details)
    @app.route('/get_sessions', methods=['GET'])
    def get_sessions():
        course_id = request.args.get('course_id')
        today_date = datetime.datetime.today().strftime('%Y-%m-%d')

        if not course_id:
            return jsonify({'success': False, 'message': 'Course ID is required'})

        # Fetch sessions that match today's date or day of the week
        query = """
             SELECT session_id, start_time, end_time, session_date
             FROM CourseSessions
             WHERE course_id = ? AND (session_date = ? OR day_of_week = ?)
             """
        day_of_week = datetime.datetime.today().strftime('%A')
        sessions = db.fetch_all(query, (course_id, today_date, day_of_week))

        sessions_data = [
            {
                'session_id': session[0],
                'time_range': f"{session[1]} - {session[2]}",
                'session_date': session[3] if session[3] else day_of_week
            } for session in sessions
        ]
        return jsonify(sessions=sessions_data)
    @app.route('/markattendance', methods=['GET', 'POST'])
    def mark_attendance_route():
        # Assuming you want to pass today's date, total registrations, etc.
        today = datetime.date.today().strftime("%Y-%m-%d")
        student_id = session.get('user_id')

        if student_id:
            # Fetch only the courses the student is enrolled in
            courses_query = """
                            SELECT c.course_id, c.course_name 
                            FROM CourseEnrollment ce
                            JOIN Courses c ON ce.course_id = c.course_id
                            WHERE ce.student_id=?
                            """
            courses = db.fetch_all(courses_query, [student_id])
        else:
            flash('Please log in to mark attendance.', 'warning')
            return redirect(url_for('login'))

        if request.method == 'POST':
            selected_course_id = request.form.get('course_id')
            # Additional logic to handle marking attendance for the selected course

        return render_template('markattendance.html', today=today, courses=courses)
        pass
    @app.route('/fetch_attendance', methods=['POST'])
    def fetch_attendance():
        if request.method == "POST" and 'username' in session:
            course_id = request.form.get('course_id', None)
            date = datetime.date.today().strftime("%Y-%m-%d")
            user_id=session['user_id']
            query = """
                      SELECT c.course_name, CONVERT(VARCHAR, s.start_time, 108) + ' - ' + CONVERT(VARCHAR, s.end_time, 108) AS session_time,
                      a.status, a.attendance_time 
                      FROM Attendance a 
                      JOIN CourseSessions s ON a.session_id = s.session_id 
                      JOIN Courses c ON s.course_id = c.course_id 
                      JOIN Users u ON a.student_id = u.UserId
                      WHERE a.attendance_date = ? and a.Student_id=?
                      """
            params = [date,user_id]

            if course_id and course_id != "":
                query += " AND s.course_id = ?"
                params.append(course_id)

            db = DatabaseConnection()  # Ensure you have a function or mechanism to get a database connection
            results = db.fetch_all(query, params)

            attendance_records = [
                {
                    'course_name': row[0],
                    'session_time': row[1],
                    'status': row[2],
                    'attendance_time': row[3].strftime("%H:%M:%S")  # Assuming 'attendance_time' is a datetime object
                }
                # {'course': row[0], 'name': row[1], 'roll_no': row[2], 'status': row[3], 'time': row[4].strftime("%H:%M %p")}
                for row in
                results]

            return jsonify({'success': True, 'attendance_records': attendance_records})
        else:
            return jsonify({'success': False, 'message': 'Unauthorized access'})
        pass

    #using Opencv2  --base feed
    # @app.route('/video_feed', methods=['GET', 'POST'])
    # def video_feed():
    #     if request.method == 'POST':
    #         if 'username' not in session:
    #             flash('Please log in to mark attendance.', 'error')
    #             return redirect(url_for('studentlogin'))
    #
    #         session_id = request.form.get('session_id')
    #         course_id = request.form.get('course_id')
    #         if not course_id:
    #             flash('No course selected. Please select a course.', 'danger')
    #             return redirect(url_for('mark_attendance_route'))
    #
    #         today = datetime.datetime.now().strftime("%Y-%m-%d")
    #         user_image_path = fetch_user_image_path(session['username'])
    #         if user_image_path is None:
    #             flash("User's image not found.", 'error')
    #             return redirect(url_for('Studentdashboard'))
    #
    #         user_image = face_recognition.load_image_file(user_image_path)
    #         user_encoding = face_recognition.face_encodings(user_image)[0]
    #
    #         video_capture = cv2.VideoCapture(0)
    #         attendance_marked = False
    #
    #         while True:
    #             ret, frame = video_capture.read()
    #             if not ret:
    #                 break
    #
    #             gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    #             faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    #
    #             face_locations = [(y, x + w, y + h, x) for (x, y, w, h) in faces]
    #
    #             face_encodings = face_recognition.face_encodings(frame, face_locations)
    #
    #             for face_encoding in face_encodings:
    #                 match = face_recognition.compare_faces([user_encoding], face_encoding)
    #                 if match[0]:
    #                     attendance_success = markattendance_db(db, session['username'],  session['user_id'],  session['roll_no'], course_id,
    #                                                            session_id, today)
    #                     if attendance_success:
    #                         flash('Attendance marked successfully.', 'success')
    #                     attendance_marked = True
    #                     break
    #
    #             if attendance_marked or cv2.waitKey(1) & 0xFF == ord('q'):
    #                 break
    #
    #         video_capture.release()
    #         cv2.destroyAllWindows()
    #         return redirect(url_for('mark_attendance_route'))
    #     pass

    @app.route('/course_enrollment', methods=['GET', 'POST'])
    def course_enrollment():
        if request.method == 'POST':
            student_id = session.get('user_id')
            course_id = request.form.get('course_id')
            enrollment_date = datetime.datetime.now()

            # Check if the student is already enrolled in the course
            existing_enrollment = db.fetch_all("SELECT * FROM CourseEnrollment WHERE student_id=? AND course_id=?", [student_id, course_id])
            if not existing_enrollment:
                db.execute_query(
                    "INSERT INTO CourseEnrollment (student_id, course_id, enrollment_date) VALUES (?, ?,?)",
                    [student_id, course_id, enrollment_date])
                flash('You have successfully enrolled in the course!', 'success')
            else:
                flash('You are already enrolled in this course.', 'warning')
            return redirect(url_for('course_enrollment'))

        student_id = session.get('user_id')
        if student_id:
            enrollments_query = """
                        SELECT ce.enrollment_id, ce.course_id, c.course_name, ce.enrollment_date 
                        FROM CourseEnrollment ce
                        JOIN Courses c ON ce.course_id = c.course_id
                        WHERE ce.student_id=?
                        """
            enrollments = db.fetch_all(enrollments_query, [student_id])
        else:
            flash('Please log in to view enrolled courses.', 'warning')
            return redirect(url_for('login'))

        courses = db.fetch_all("SELECT * FROM Courses")
        return render_template('course_enrollment.html', courses=courses, enrollments=enrollments)

    @app.route('/video_feed', methods=['GET', 'POST'])
    def video_feed():
        if request.method == 'POST':
            if 'username' not in session:
                flash('Please log in to mark attendance.', 'error')
                return redirect(url_for('studentlogin'))

            session_id = request.form.get('session_id')
            course_id = request.form.get('course_id')
            if not session_id or not course_id:
                flash('No session or course selected. Please select a session and course.', 'danger')
                return redirect(url_for('mark_attendance_route'))

            today = datetime.datetime.now().strftime("%Y-%m-%d")


            ##########  code for face recognition  ####

            user_image_path = fetch_user_image_path(session['username'])
            if user_image_path is None or not os.path.exists(user_image_path):
                flash("User's image not found. Please ensure your profile image has been uploaded.", 'error')
                return redirect(url_for('Studentdashboard'))

            user_image = face_recognition.load_image_file(user_image_path)
            user_encoding = face_recognition.face_encodings(user_image)[0]

            script_dir = os.path.dirname(os.path.abspath(__file__))  # Gets the directory of the current script
            encode_file_path = os.path.join(script_dir, "EncodeFile.p")  # Builds the path to 'EncodeFile.p'

            print("Loading Encode File...")
            try:
                with open(encode_file_path, 'rb') as file:
                    encodeListKnownWithIds = pickle.load(file)
                encodeListKnown, studentIds = encodeListKnownWithIds
            except FileNotFoundError:
                print(f"FileNotFoundError: No such file or directory: '{encode_file_path}'")

            video_capture = cv2.VideoCapture(0)
            video_capture.set(3, 640)
            video_capture.set(4, 480)

            attendance_marked = False
            process_complete = False

            last_action_time = time.time()
            action_timeout = 2  # 2 seconds

            while True:
                success, img = video_capture.read()
                if not success:
                    break
                current_time = time.time()

                if not success or (current_time - last_action_time > action_timeout and process_complete ):
                    break
                imgs=cv2.resize(img,(0,0),None, 0.25,0.25)
                img= cv2.cvtColor(img,cv2.COLOR_BGR2RGB)

                faceCurFrame=face_recognition.face_locations(imgs)
                encodeCurFrame=face_recognition.face_encodings(imgs,faceCurFrame)

                # face_detected_and_processed = False
                face_detected = len(faceCurFrame) > 0
                face_processed = False

                for encodeFace, faceLoc in zip(encodeCurFrame, faceCurFrame):
                    matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
                    faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)

                    if matches:
                        matchIndex = np.argmin(faceDis)
                        if matches[matchIndex]:
                            # Known face detected
                            recognized_id = studentIds[matchIndex]
                            recognized_username = recognized_id.split('_')[0]

                            if recognized_username == session.get('username'):
                                if not attendance_marked:
                                    markattendance_db(db, session['user_id'], session_id, today)
                                    cv2.putText(img, "Attendance Marked Successfully", (50, 50),
                                                cv2.FONT_HERSHEY_SIMPLEX,
                                                1, (0, 255, 0), 2)
                                    attendance_marked = True
                                    # process_complete = True
                                    # face_detected_and_processed = True
                                    # break
                                else:
                                    cv2.putText(img, "Attendance Already Marked", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1,
                                                (0, 255, 255), 2)
                                    face_processed = True
                                    break

                            else:
                                cv2.putText(img, "Face Not Associated With Logged-In User", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                                face_processed = True

                        else:
                            cv2.putText(img, "Face Not Recognized", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0),2)
                            face_processed = True

                # if face_detected_and_processed or not faceCurFrame:
                #     last_action_time = time.time()
                if face_processed or not face_detected:
                    last_action_time = current_time

                cv2.imshow('Face Recognition', img)

                if cv2.waitKey(1) & 0xFF == ord('q') or process_complete or (face_processed and (current_time - last_action_time > action_timeout)):
                #if cv2.waitKey(1) & 0xFF == ord('q') or process_complete or ( not face_detected and (current_time - last_action_time > action_timeout)):
                # if cv2.waitKey(1) & 0xFF == ord('q') or process_complete or (current_time - last_action_time > action_timeout):
                # if cv2.waitKey(1) & 0xFF == ord('q') or process_complete:
                    break

            video_capture.release()
            cv2.destroyAllWindows()
            return redirect(url_for('mark_attendance_route'))