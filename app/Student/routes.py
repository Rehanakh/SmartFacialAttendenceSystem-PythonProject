import pickle
import numpy as np
from flask import Flask,Blueprint, current_app, render_template, request, flash, redirect, url_for, jsonify,Response,session
from .services import fetch_user_details,fetch_user_image_path,register_user ,known_faces,known_names,update_encodings,is_face_unique,capture_image_from_webcam,get_attendance_records,get_attendance_data,get_attendance_trends_with_courses,predict_risk,create_temp_user
from .attendance import markattendance_db
from app.util.connection import DatabaseConnection
import face_recognition
import datetime
import os
import time
import shutil
from flask_mail import Message
import random
from .models import CourseSession
from sqlalchemy import or_
from deepface import DeepFace
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
            session['temp_image_path'] = captured_image_path

            try:
                new_user_image = face_recognition.load_image_file(captured_image_path)
                new_user_encoding = face_recognition.face_encodings(new_user_image)[0]

                # Step 2: Check if the face is unique
                if not is_face_unique(new_user_encoding):
                    flash('A similar face has already been registered.', 'error')
                    if os.path.exists(captured_image_path):
                        os.remove(captured_image_path)
                    return render_template('registration.html')
            except IndexError:
                flash("No face detected in the image. Please try again.", "error")
                if os.path.exists(captured_image_path):
                    os.remove(captured_image_path)
                return render_template('registration.html')

            # # Construct the permanent image path #moving after verifying otp
            # img_name = f"{username}_{roll_no}.jpg"
            # permanent_image_path = os.path.join(current_app.root_path, 'app', 'static', 'faces', img_name)
            #
            # # Move the image from the temporary path to the permanent path
            # shutil.move(captured_image_path, permanent_image_path)


            # Generate OTP and send it via email before completing registration
            otp = random.randint(100000, 999999)
            session['otp'] = otp  # Store OTP in session for verification

            user_details = {
                'username': username,
                'email': email,
                'fullname': full_name,
                'roll_no': roll_no,
                'password': password,
                # 'captured_image_path': permanent_image_path,
                'captured_image_path':captured_image_path,
                'userType': userType,
                'status': status
            }

            create_temp_user(user_details, otp)

            email_subject = "Your Registration OTP"
            email_body = f"Here is your OTP for registration: {otp}"
            send_otp_email(email, email_subject, email_body)

            # Here you save all necessary information into the session
            session['form_data'] = {
                'userType': userType,
                'status': status,
                'username': username,
                'roll_no': roll_no,
                'email': email,
                'full_name': full_name,
                'password': password,
                'captured_image_path': captured_image_path
                # Assuming this variable holds the path to the captured image
            }

            # Redirect to an OTP verification page, you need to implement this
            return redirect(url_for('verify_otp'))

        return render_template('registration.html')

    @app.route('/Studentdashboard')
    def Studentdashboard():
        if 'username' not in session:
            # Redirect to login page if user is not logged in
            return redirect(url_for('login'))

        student_id = session['user_id']
        attendance_raw_data = get_attendance_data(student_id)
        attendance_trends_raw_data = get_attendance_trends_with_courses(student_id)

        # courses = {item['course_name'] for item in attendance_trends_raw_data}
        # Assuming each tuple is structured like (attendance_date, status, count, course_name)
        # courses = {item[3] for item in attendance_trends_raw_data}  # item[3] is where the course_name is expected to be

        # Assuming attendance_trends_raw_data now includes course_id and course_name
        courses = [
            {"course_id": item[4], "course_name": item[3]}
            for item in attendance_trends_raw_data
        ]
        # course_ids = [course['course_id'] for course in courses]
        course_ids = [entry[4] for entry in attendance_trends_raw_data]  # Assuming index 4 is where the course_id is

        # Remove duplicates, preserving order
        seen = set()
        courses = [x for x in courses if x['course_id'] not in seen and not seen.add(x['course_id'])]

        attendance_data = {
            'statuses': [item[0] for item in attendance_raw_data],
            'counts': [item[1] for item in attendance_raw_data]
        }

        formatted_trends_data = {}
        for date, status, count, course_name,course_id in attendance_trends_raw_data:
            if isinstance(date, datetime.date):
                formatted_date = date.strftime("%d-%m-%Y")
            else:
                # If 'date' is somehow a string, parse it first
                # This is just a fallback and may not be necessary
                parsed_date = datetime.datetime.strptime(date, "%a, %d%B %Y %H:%M:%S GMT")
                formatted_date = parsed_date.strftime("%d-%m-%Y")
            # Assuming date is a string that needs to be parsed into a datetime object
            # Adjust the format in strptime if your date format is different
            # parsed_date = datetime.datetime.strptime(date, "%a, %d%B %Y %H:%M:%S GMT")  # Example format
            # formatted_date = parsed_date.strftime("%d-%m-%Y")  # Desired format: DD-MM-YYYY

            if formatted_date not in formatted_trends_data:
                formatted_trends_data[formatted_date] = 0
            formatted_trends_data[formatted_date] += count


        # # Assuming you want to aggregate counts by date for trends
        # trends_data = {}
        # for date, status, count in attendance_trends_raw_data:
        #     if date not in trends_data:
        #         trends_data[date] = 0
        #     trends_data[date] += count

        attendance_trends = {
            'dates': list(formatted_trends_data.keys()),
            'counts': list(formatted_trends_data.values())
        }

        risk_status = predict_risk(student_id)
        # You can also pass the scores and attendance summary to the template if needed


        return render_template('studentdashboard.html', attendance_data=attendance_data,
                               attendance_trends=attendance_trends, risk_status=risk_status,courses=list(courses),courseIds=course_ids)

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
        selected_course_id = request.form.get('course_id')

        if student_id:
            # Fetch only the courses the student is enrolled in
            courses_query = """
                            SELECT c.course_id, c.course_name 
                            FROM CourseEnrollment ce
                            JOIN Courses c ON ce.course_id = c.course_id
                            WHERE ce.student_id=? and ce.status='Accepted'
                            """
            courses = db.fetch_all(courses_query, [student_id])
        else:
            flash('Please log in to mark attendance.', 'warning')
            return redirect(url_for('login'))

        if request.method == 'POST':
            selected_course_id = request.form.get('course_id')
            # Additional logic to handle marking attendance for the selected course

        return render_template('markattendance.html', today=today, courses=courses, selected_course_id=selected_course_id)
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
                    "INSERT INTO CourseEnrollment (student_id, course_id, enrollment_date,status) VALUES (?, ?,?,?)",
                    [student_id, course_id, enrollment_date, 'Requested'])
                flash('Course request submitted.', 'success')
            else:
                flash('You are already enrolled in this course.', 'warning')
            return redirect(url_for('course_enrollment'))

        courses = db.fetch_all("SELECT * FROM Courses")
        # Fetch enrollments where status is 'Approved' or requests made by the student
        enrollments = db.fetch_all(
            "SELECT ce.*, c.course_name FROM CourseEnrollment ce JOIN Courses c ON ce.course_id = c.course_id WHERE ce.student_id=? AND (ce.status='Accepted' OR ce.status='Requested' OR ce.status='Requested Removal')",
            [session.get('user_id')])
        return render_template('course_enrollment.html', courses=courses, enrollments=enrollments)

    @app.route('/drop_course/<enrollment_id>', methods=['POST'])
    def drop_course(enrollment_id):
        student_id = session.get('user_id')
        if not student_id:
            flash('Please log in to manage courses.', 'warning')
            return redirect(url_for('login'))

        # Verify that the enrollment belongs to the logged-in student
        enrollment = db.fetch_all("SELECT * FROM CourseEnrollment WHERE enrollment_id=? AND student_id=? AND status='Accepted'",
                                  [enrollment_id, student_id])
        if enrollment:
            db.execute_query("UPDATE CourseEnrollment SET status='Requested Removal' WHERE enrollment_id=?",
                             [enrollment_id])
            # db.execute_query("DELETE FROM CourseEnrollment WHERE enrollment_id=?", [enrollment_id])
            flash('Removal request submitted.', 'info')  # Updated message to indicate request submission

        else:
            flash('Course could not be found or does not belong to you.', 'error')

        return redirect(url_for('course_enrollment'))

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

                if not success or (current_time - last_action_time > action_timeout and process_complete) or attendance_marked:
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

                    matchIndex = np.argmin(faceDis) if matches else None
                    if matchIndex is not None  and not attendance_marked:
                        #comment sacling frame coordinates for now
                        # y1, x2, y2, x1 = faceLoc
                        # y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4  # Scale back up face location since the frame was scaled to 1/4 size
                        # cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        # Draw a rectangle around the face
                        # recognized_id = studentIds[matchIndex]
                        # recognized_username = recognized_id.split('_')[0]

                        recognized_username = studentIds[matchIndex].split('_')[0]

                        # Known face detected
                        if recognized_username == session.get('username'):
                            cv2.putText(img, "Press 'q' to mark attendance", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1,
                                        (0, 255, 0), 2)
                            cv2.imshow('Face Recognition', img)
                            if cv2.waitKey(1) & 0xFF == ord('q'):
                                face_image = img[faceLoc[0] * 4:faceLoc[2] * 4, faceLoc[3] * 4:faceLoc[1] * 4]
                                face_image = cv2.cvtColor(face_image, cv2.COLOR_RGB2BGR)
                                try:
                                    analysis = DeepFace.analyze(face_image, actions=['emotion'], enforce_detection=False)
                                    print(analysis)
                                    # dominant_emotion = analysis["dominant_emotion"]
                                    # Access the first element of the list, then the 'dominant_emotion' from the dictionary
                                    dominant_emotion = analysis[0]["dominant_emotion"]

                                    print("Detected emotion:", dominant_emotion)
                                    cv2.putText(img, f"Emotion: {dominant_emotion}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                except Exception as e:
                                    print(f"Emotion detection failed: {e}")

                                    #Mark attendance in db
                                markattendance_db(db, session['user_id'], session_id, course_id, today,dominant_emotion)
                                cv2.putText(img, "Attendance Marked Successfully", (50, 100), cv2.FONT_HERSHEY_SIMPLEX,
                                            1,
                                            (0, 255, 0), 2)
                                cv2.imshow('Face Recognition', img)
                                cv2.waitKey(5000)  # Wait for 5 seconds
                                attendance_marked = True
                                time.sleep(2)
                                break
                            #comment below code to change functionality to detect emotions with attendance
                            # if not attendance_marked:
                            #     cv2.rectangle(img, (faceLoc[3] * 4, faceLoc[0] * 4),
                            #                   (faceLoc[1] * 4, faceLoc[2] * 4),
                            #                   (0, 255, 0), 2)
                            #     cv2.putText(img, "Press 'q' to mark attendance", (50, 50), cv2.FONT_HERSHEY_SIMPLEX,
                            #                 1,
                            #                 (0, 255, 0), 2)
                            #     cv2.imshow('Face Recognition', img)
                            #     key = cv2.waitKey(1) & 0xFF
                            #     if key == ord('q'):
                            #         top, right, bottom, left = faceLoc
                            #         face_image = img[top:bottom, left:right]
                            #         face_image = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
                                    # try:
                                    #     analysis = DeepFace.analyze(face_image, actions=['emotion'])
                                    #     dominant_emotion = analysis["dominant_emotion"]
                                    #     cv2.putText(img, f"Emotion: {dominant_emotion}", (50, 100),
                                    #                 cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                    #
                                    #     cv2.putText(img, f"Emotion: {dominant_emotion}", (50, 100),
                                    #                 cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                    # except Exception as e:
                                    #     print(f"Emotion detection failed: {e}")
                                    #
                                    # markattendance_db(db, session['user_id'], session_id, course_id, today)
                                    # # cv2.putText(img, "Attendance Marked Successfully", (50, 50),  cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                    # cv2.putText(img, "Attendance Marked Successfully", (50, 150),
                                    #             cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                    # attendance_marked = True
                                    # time.sleep(2)
                                    # break
                            # else:
                            #     cv2.putText(img, "Attendance Already Marked", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1,
                            #                 (0, 255, 255), 2)
                            #     face_processed = True
                            #     break

                        else:
                            cv2.putText(img, "Face Not Associated With Logged-In User", (50, 50),
                                            cv2.FONT_HERSHEY_SIMPLEX, 1,
                                            (0, 0, 255), 2)
                            face_processed = True
                    else:
                        cv2.putText(img, "Face Not Recognized", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
                        face_processed = True

                cv2.imshow('Face Recognition', img)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            video_capture.release()
            cv2.destroyAllWindows()
            return redirect(url_for('mark_attendance_route'))
    def send_otp_email(to_email, subject, body):
        mail = current_app.extensions['mail']
        msg = Message(subject,
                      recipients=[to_email],
                      body=body)
        mail.send(msg)

    def send_welcome_email(to_email,user_name):
        mail = current_app.extensions['mail']
        subject = "Welcome to Smart Attendance System"
        message_body = f"Dear {user_name},\n\n" \
                       "Welcome to Smart Attendance System! We're excited to have you on board. " \
                       "This system allows for efficient and secure attendance tracking using state-of-the-art " \
                       "facial recognition technology.\n\n" \
                       "Thank you for choosing us.\n\n" \
                       "Best regards,\nThe Smart Attendance System Team"
        msg = Message(subject, recipients=[to_email], body=message_body)
        try:
            mail.send(msg)
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False

    @app.route('/verify_otp', methods=['GET', 'POST'])
    def verify_otp():
        if request.method == 'POST':
            user_otp = request.form['otp']
            if 'otp' in session and int(user_otp) == session['otp']:
                db = DatabaseConnection()
                temp_users = db.fetch_all('SELECT * FROM temp_users WHERE OTP = ? AND ExpiresAt > ?',(user_otp, datetime.datetime.now()))
                print(f"Temp user fetched from database: {temp_users}")  # Prints the fetched user details

                # session.pop('otp', None)  # Clear the OTP
                # All the user's registration information is stored in session['form_data']
                # user_details = session.get('form_data',None)
                if temp_users:
                    temp_user = temp_users[0]  # Assuming fetch_all returns a list of tuples and we take the first one
                    temp_user_dict = {
                        'username': temp_user[1],
                        'email': temp_user[2],
                        'full_name': temp_user[3],
                        'roll_no': temp_user[4],
                        'password': temp_user[5],
                        'captured_image_path': temp_user[6],
                        'userType': temp_user[7],
                        'status': temp_user[8],
                        # Add more fields as per your database schema
                    }
                    username = temp_user[1]
                    roll_no = temp_user[4]
                    captured_image_path = temp_user[6]

                    # Move the image to a permanent location
                    img_name = f"{username}_{roll_no}.jpg"
                    # img_name = f"{temp_user['username']}_{temp_user['roll_no']}.jpg"
                    permanent_image_path = os.path.join(current_app.root_path, 'app', 'static', 'faces', img_name)
                    shutil.move(temp_user_dict['captured_image_path'], permanent_image_path)

                    temp_user_dict['captured_image_path'] = permanent_image_path  # Update path to permanent

                    try:
                        if register_user(temp_user_dict):
                            db.execute_query('DELETE FROM temp_users WHERE TempUserId = ?', (temp_user[0],))
                            update_encodings()
                            db.commit()
                            flash('OTP verified successfully! Registration complete.', 'success')
                            send_welcome_email(temp_user_dict['email'], temp_user_dict['full_name'])
                            return redirect(url_for('registration'))  # Redirect to the dashboard or relevant page
                        else:
                            flash('Registration failed. Please try again.', 'error')
                            return redirect(url_for('Studentdashboard'))  # Assume you redirect to a dashboard

                    except Exception as e:
                        print(f"Error during registration: {e}")
                        flash('An error occurred during registration. Please try again.', 'error')
                    else:
                        flash('Invalid or expired OTP.', 'error')

                    return redirect(url_for('registration'))

        return render_template('verify_otp.html')
    @app.route('/attendance_history', methods=['GET'])
    def attendance_history():
        if 'username' not in session:
            return redirect(url_for('login'))

        selected_course = request.args.get('course', None)
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Adjust as needed

        db = DatabaseConnection()
        # Assume get_attendance_records is defined in services.py
        attendance_records, total_records = get_attendance_records(session['user_id'],selected_course, page, per_page)
        courses = db.fetch_all("SELECT * FROM Courses")

        # Calculate total pages for pagination
        total_pages = (total_records + per_page - 1) // per_page

        return render_template('attendance_history.html',
                               attendance_records=attendance_records,
                               courses=courses,
                               selected_course=selected_course,
                               page=page,
                               total_pages=total_pages,
                               per_page=per_page)

    @app.route('/get_risk_data/<int:student_id>')
    def get_risk_data(student_id):
        risk_status = predict_risk(student_id)  # Use the existing predict_risk function
        if risk_status == "Data Unavailable":
            return jsonify({"error": "Data unavailable for the given student ID"}), 404

        risk_value = 75 if risk_status == "At Risk" else 25  # Example risk calculation based on status

        response = {
            "labels": ["At Risk", "Not At Risk"],
            "data": [risk_value, 100 - risk_value],
            "backgroundColor": ['rgba(255, 99, 132, 0.6)' if risk_status == "At Risk" else 'rgba(75, 192, 192, 0.6)',
                                'rgba(201, 203, 207, 0.2)'],
            "riskStatus": risk_status
        }
        return jsonify(response)

    @app.route('/notifications')
    def notifications():
        student_id = session.get('user_id')
        # print("Student ID:", student_id)  # Debug: print the student ID

        if not student_id:
            return jsonify([]), 401

        query = """
            SELECT cs.course_id, c.course_name, cs.start_time, cs.day_of_week
            FROM CourseSessions cs
            JOIN CourseEnrollment e ON cs.course_id = e.course_id
            JOIN Courses c ON cs.course_id = c.course_id
            WHERE e.student_id = ? AND cs.day_of_week = 
            (SELECT CASE DATENAME(WEEKDAY, GETDATE())
                WHEN 'Monday' THEN 'Tuesday'
                WHEN 'Tuesday' THEN 'Wednesday'
                WHEN 'Wednesday' THEN 'Thursday'
                WHEN 'Thursday' THEN 'Friday'
                WHEN 'Friday' THEN 'Saturday'
                WHEN 'Saturday' THEN 'Sunday'
                WHEN 'Sunday' THEN 'Monday'
                ELSE cs.day_of_week
            END)
        """
        try:
            upcoming_classes = db.fetch_all(query, [student_id])
            formatted_classes = [
                {
                    "course_id": course[0],
                    "course_name": course[1],
                    "start_time": course[2].strftime("%H:%M"),  # Format time as string
                    "day_of_week": course[3]
                }
                for course in upcoming_classes
            ]
            return jsonify(formatted_classes)
        except Exception as e:
            print("Error fetching classes:", str(e))  # Debug: print any errors
            return jsonify({'error': str(e)}), 500




