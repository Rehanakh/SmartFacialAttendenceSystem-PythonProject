from flask import Flask, Blueprint, render_template, request, flash, redirect, url_for, jsonify, Response, session

from app.Professor.Services import register_user, fetch_user_details
from app.util.connection import DatabaseConnection
import face_recognition
import datetime
import os
import time
import cv2
import logging

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

# ... other routes specific to professors ...
