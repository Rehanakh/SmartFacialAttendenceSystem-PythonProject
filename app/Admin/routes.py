from flask import Flask,Blueprint, render_template, request, flash, redirect, url_for, jsonify,Response,session

from app.Admin.Services import register_user, fetch_user_details
from app.util.connection import DatabaseConnection
# import face_recognition
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

def setup_routes(app):
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
                return redirect(url_for('Admindashboard') + '?login_success=1')

            else:
                # If the user was not found, flash an error message
                flash('Login failed. User not found.', 'error')

            # Display the login page with or without the login_success flag
        return render_template('adminlogin1.html', login_success=request.args.get('login_success', '0'))
        pass

    @app.route('/logout')
    def logout():
        logging.debug('Logging out user.')
        # Clear the session
        session.clear()
        # flash('You have been logged out.', 'success')
        return redirect(url_for('home'))
        pass





