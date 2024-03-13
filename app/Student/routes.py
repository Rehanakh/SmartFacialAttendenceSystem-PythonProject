from flask import Flask,Blueprint, render_template, request, flash, redirect, url_for, jsonify,Response,session
from .services import fetch_user_details,fetch_user_image_path,register_user
from app.util.connection import DatabaseConnection
import face_recognition
import datetime
import os
import time
import cv2
import logging
logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s:%(levelname)s:%(message)s')
#print("key",os.urandom(24))

known_faces = []
known_names = []
today= datetime.date.today().strftime("%d_%m_%Y").replace("_","-")
db = DatabaseConnection()

def student_setup_routes(app):
    @app.route('/')
    def home():
        # return 'Hello, World!'
        return render_template('home.html')

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

            registration_successful = register_user(userType, status, username, roll_no, email, full_name, password)

            if registration_successful:
                flash('Registration Successful!', 'success')
            else:
                flash('Registration Failed! User Already Exists', 'error')

            return redirect(url_for('registration'))
        else:
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