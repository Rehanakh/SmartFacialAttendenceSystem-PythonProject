from flask import Flask, Blueprint, render_template, request, flash, redirect, url_for, jsonify, Response, session

from app.Professor.Services import register_user, fetch_user_details
from app.util.connection import DatabaseConnection
import face_recognition
import datetime
import os
import time
import cv2
import logging
import pyodbc

logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s:%(levelname)s:%(message)s')

known_faces = []
known_names = []
today = datetime.date.today().strftime("%d_%m_%Y").replace("_", "-")
db = DatabaseConnection()

def professor_setup_routes(app):
    @app.route('/')
    def Professor_home():
        return render_template('home.html')

    @app.route('/Professor_registration', methods=['GET', 'POST'])
    def Professor_registration():
        if request.method == 'POST':
            userType = request.form.get('userType', 'defaultType')  # Change default type to 'P' for Professor
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
                return render_template('registration.html')

            registration_successful = register_user(userType, status, username, roll_no, email, full_name, password)

            if registration_successful:
                flash('Registration Successful!', 'success')
            else:
                flash('Registration Failed! User Already Exists', 'error')

            return redirect(url_for('registration'))
        else:
            return render_template('registration.html')

    @app.route('/ProfessorDashboard')
    def Professor_dashboard():
        if 'username' not in session:
            return redirect(url_for('login'))
        return render_template('ProfessorDashboard.html')
    @app.route('/home', methods=['GET'], endpoint='professor_home_endpoint')
    def professor_home():
        # Assuming 'home.html' is the name of your HTML file with the navbar
        return render_template('home.html')
        pass

    @app.route('/', methods=['GET'], endpoint='professor_index')
    def index():
        return redirect(url_for('home'))
        pass
    @app.route('/ProfessorLogin', methods=['GET', 'POST'])
    def ProfessorLogin():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']

            user = fetch_user_details(username)

            if user and user.PasswordHash == password:
                session['user_id'] = user.UserId
                session['username'] = user.Username
                session.permanent = True
                return redirect(url_for('Professor_dashboard') + '?login_success=1')
            else:
                flash('Login failed. User not found.', 'error')

        return render_template('ProfessorLogin.html', login_success=request.args.get('login_success', '0'))

    @app.route('/Pofessorlogout')
    def Professor_logout():
        logging.debug('Logging out user.')
        session.clear()
        return redirect(url_for('home'))

    @app.route('/ProfessorUpdateProfile', methods=['GET', 'POST'])
    def ProfessorUpdateProfile():
        if 'username' not in session:
            flash('Please log in to view this page.', 'error')
            return redirect(url_for('ProfessorLogin'))

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
                return redirect(url_for('ProfessorUpdateProfile'))

            # Construct the SQL query to update user details
            query = "UPDATE users SET Username=?, Email=?, FullName=?, RollNumber=? WHERE UserId = ?"
            db.execute_query(query, (new_username, email, full_name, roll_number, user_id))
            session['username'] = new_username
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('ProfessorUpdateProfile'))

        return render_template('ProfessorUpdateProfile.html', user=user_details)

    @app.route('/ProfessorSession', methods=['GET', 'POST'])
    def ProfessorSession():
        if request.method == 'POST':
            course_id = request.form.get('course_id')
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')
            day_of_week = request.form.get('day_of_week')
            session_date = request.form.get('session_date')

            # Assuming you have a function to insert session data into the database
            insert_session_data(course_id, start_time, end_time, day_of_week, session_date)
            flash('Session created successfully!', 'success')
            return redirect(url_for('ProfessorSession'))  # Redirect to the same route after form submission

        else:
            # Fetch course names from the database
            db_connection = DatabaseConnection()
            courses = db_connection.fetch_all("SELECT course_id, course_name FROM Courses")

            # Fetch session data from the database
            sessions = db_connection.fetch_all("SELECT * FROM CourseSessions")
            db_connection.close()

            return render_template('ProfessorSession.html', courses=courses, sessions=sessions)

    def insert_session_data(course_id, start_time, end_time, day_of_week, session_date):
        try:
            db_connection = DatabaseConnection()
            query = "INSERT INTO CourseSessions (course_id, start_time, end_time, day_of_week, session_date) VALUES (?, ?, ?, ?, ?)"
            params = (course_id, start_time, end_time, day_of_week, session_date)
            db_connection.execute_query(query, params)
            db_connection.close()
        except Exception as e:
            print("Error inserting session data:", e)
            # Handle insertion errors as needed

    @app.route('/ProfessorEnrollment', methods=['GET', 'POST'])
    def ProfessorEnrollment():
        if request.method == 'POST':
            enrollment_id = request.form.get('enrollment_id')
            action = request.form.get('action')  # Either 'accept' or 'decline'

            if action == 'accept':
                # Update status to 'Accepted' in the database
                update_enrollment_status(enrollment_id, 'Accepted')
                flash('Enrollment request accepted successfully!', 'success')
            elif action == 'decline':
                # Update status to 'Declined' in the database
                update_enrollment_status(enrollment_id, 'Declined')
                flash('Enrollment request declined successfully!', 'danger')

            return redirect(url_for('ProfessorEnrollment'))

        else:
            # Fetch enrollment requests from the database
            enrollments = fetch_enrollments()
            return render_template('ProfessorEnrollment.html', enrollments=enrollments)

    def fetch_enrollments():
        try:
            # Create an instance of the DatabaseConnection class
            db_connection = DatabaseConnection()

            # SQL query to fetch enrollments from the CourseEnrollment table
            query = "SELECT * FROM CourseEnrollment"

            # Fetch all enrollments using the execute_query method
            enrollments = db_connection.fetch_all(query)

            # Close the database connection
            db_connection.close()

            return enrollments

        except Exception as e:
            print("Error fetching enrollments:", e)
            return []

    def update_enrollment_status(enrollment_id, status):
        try:
            # Create an instance of the DatabaseConnection class
            db_connection = DatabaseConnection()

            # SQL query to update enrollment status
            query = "UPDATE CourseEnrollment SET status = ? WHERE enrollment_id = ?"
            params = (status, enrollment_id)

            # Execute the query
            db_connection.execute_query(query, params)

            # Commit the transaction
            db_connection.commit()

            # Close the database connection
            db_connection.close()

        except Exception as e:
            print("Error updating enrollment status:", e)

    def fetch_attendance_by_session(session_id):
        db_connection = DatabaseConnection()
        try:
            query = "SELECT * FROM Attendance WHERE session_id = ?"
            attendances = db_connection.fetch_all(query, (session_id,))
            return attendances
        except Exception as e:
            print("Error fetching attendance by session:", e)
            return []

    def update_attendance_status(attendance_id, status):
        db_connection = DatabaseConnection()
        try:
            query = "UPDATE Attendance SET status = ? WHERE id = ?"
            db_connection.execute_query(query, (status, attendance_id))
        except Exception as e:
            print("Error updating attendance status:", e)
    @app.route('/Manage_attendance', methods=['GET', 'POST'])
    def Manage_attendance():
        if request.method == 'POST':
            session_id = request.form['session_id']
            attendances = fetch_attendance_by_session(session_id)
            return render_template('Manage_attendance.html', session_id=session_id, attendances=attendances)
        else:
            # Add a return statement for the GET request
            return render_template('Manage_attendance.html')

    @app.route('/update_attendance', methods=['POST'])
    def update_attendance():
        if request.method == 'POST':
            session_id = request.form['session_id']
            for key, value in request.form.items():
                if key.startswith('status_'):
                    attendance_id = key.split('_')[1]
                    update_attendance_status(attendance_id, value)
            return redirect(url_for('Manage_attendance', session_id=session_id))
