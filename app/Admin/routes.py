from flask import Flask, Blueprint, render_template, request, flash, redirect, url_for, jsonify, Response, session

from app.Admin.Services import register_user, fetch_user_details, fetch_all_usernames_and_statuses, update_user_status, \
    get_attendance_records
from app.util.connection import DatabaseConnection
import face_recognition
import datetime
import os
import time
import cv2
import logging

logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s:%(levelname)s:%(message)s')
# print("key",os.urandom(24))

known_faces = []
known_names = []
today = datetime.date.today().strftime("%d_%m_%Y").replace("_", "-")
db = DatabaseConnection()


def admin_setup_routes(app):
    @app.route('/')
    def admin_home():
        # return 'Hello, World!'
        return render_template('home.html')

    @app.route('/admin_registration', methods=['GET', 'POST'])
    def admin_registration():
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

            registration_successful = register_user(userType, status, username, roll_no, email, full_name, password)

            if registration_successful:
                flash('Registration Successful!', 'success')
            else:
                flash('Registration Failed! User Already Exists', 'error')

            return redirect(url_for('registration'))
        else:
            return render_template('registration.html')

    @app.route('/Admindashboard')
    def Admindashboard():
        if 'username' not in session:
            # Redirect to login page if user is not logged in
            return redirect(url_for('login'))
        return render_template('Admindashboard.html')
        pass

    @app.route('/adminlogin1', methods=['GET', 'POST'])
    def adminlogin1():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            # Validate login credentials (this is a placeholder, implement your validation logic)
            return redirect('/markattendance')  # Redirect to the attendance marking page
        return render_template('adminlogin1.html')
        pass

    @app.route('/home', methods=['GET'], endpoint='admin_home_endpoint')
    def admin_home():
        # Assuming 'home.html' is the name of your HTML file with the navbar
        return render_template('home.html')
        pass

    @app.route('/users', methods=['GET'], endpoint='admin_user_endpoint')
    def users():
        usernames_statuses = fetch_all_usernames_and_statuses()
        return render_template('users.html', usernames_statuses=usernames_statuses)

    @app.route('/', methods=['GET'], endpoint='admin_index')
    def index():
        return redirect(url_for('home'))
        pass

    @app.route('/admin_login', methods=['GET', 'POST'])
    def admin_login():  # To Login Student after putting credentials on Student Login page
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
                # change:03-03-2024
                return redirect(url_for('Admindashboard') + '?login_success=1')

            else:
                # If the user was not found, flash an error message
                flash('Login failed. User not found.', 'error')

            # Display the login page with or without the login_success flag
        return render_template('adminlogin1.html', login_success=request.args.get('login_success', '0'))
        pass

    @app.route('/admin_logout')
    def admin_logout():
        logging.debug('Logging out user.')
        # Clear the session
        session.clear()
        # flash('You have been logged out.', 'success')
        return redirect(url_for('home'))
        pass

    @app.route('/AdminUpdateProfile', methods=['GET', 'POST'])
    def AdminUpdateProfile():
        if 'username' not in session:
            flash('Please log in to view this page.', 'error')
            return redirect(url_for('adminlogin1'))

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

        return render_template('AdminUpdateProfile.html', user=user_details)

    @app.route('/approve/<username>', methods=['POST'])
    def approve_user(username):
        # Call service method to update status in the database
        success = update_user_status(username, 'Approved')  # Assuming you have a service method to update the status
        if success:
            return 'User approved successfully', 200
        else:
            return 'Failed to approve user', 500

    @app.route('/decline/<username>', methods=['POST'])
    def decline_user(username):
        success = update_user_status(username, 'Declined')  # Assuming you have a service method to update the status
        if success:
            return 'User declined successfully', 200
        else:
            return 'Failed to decline user', 500

    # @app.route('/attendance_admin_history', methods=['GET'])
    # def attendance_admin_history():
    #     if 'username' not in session:
    #         return redirect(url_for('login'))
    #
    #     selected_course = request.args.get('course', None)
    #     page = request.args.get('page', 1, type=int)
    #     per_page = 10  # Adjust as needed
    #
    #     db = DatabaseConnection()
    #     # Assume get_attendance_records is defined in services.py
    #     attendance_records, total_records = get_attendance_records(session['user_id'], selected_course, page, per_page)
    #     courses = db.fetch_all("SELECT * FROM Courses")
    #     students = db.fetch_all("SELECT DISTINCT student_id FROM Attendance")
    #     # Calculate total pages for pagination
    #     total_pages = (total_records + per_page - 1) // per_page
    #
    #     return render_template('attendance_admin_history.html',
    #                            attendance_records=attendance_records,
    #                            courses=courses,
    #                            students=students,
    #                            selected_course=selected_course,
    #                            page=page,
    #                            total_pages=total_pages,
    #                            per_page=per_page)
    @app.route('/attendance_admin_history', methods=['GET'])
    def attendance_admin_history():
        if 'username' not in session:
            return redirect(url_for('login'))

        selected_course = request.args.get('course')
        selected_student = request.args.get('student')
        page = request.args.get('page', 1, type=int)
        per_page = 10

        db = DatabaseConnection()

        # Retrieve attendance records based on selected student, course, and pagination parameters
        attendance_records, total_records = get_attendance_records(student_id=selected_student,
                                                                   course_id=selected_course,
                                                                   page=page,
                                                                   per_page=per_page)

        # Fetch courses and distinct student IDs for dropdown population
        courses = db.fetch_all("SELECT * FROM Courses")
        students = db.fetch_all("SELECT DISTINCT student_id FROM Attendance")

        # Calculate total pages for pagination
        total_pages = (total_records[0] + per_page - 1) // per_page

        return render_template('attendance_admin_history.html',
                               attendance_records=attendance_records,
                               courses=courses,
                               students=students,
                               selected_course=selected_course,
                               selected_student=selected_student,
                               page=page,
                               total_pages=total_pages,
                               per_page=per_page)


