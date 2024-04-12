
from app.Student.models import User
from app.util.connection import DatabaseConnection
# import face_recognition

from flask import current_app
import time
import cv2
import os
from flask import flash

db = DatabaseConnection()

def fetch_user_details(username):
    query = "SELECT UserId, Username, Email, FullName, RollNumber, PasswordHash FROM users WHERE Username = ? AND UserType = 'P' "
    db = DatabaseConnection()
    results = db.fetch_all(query, (username,))
    if results:
        user_data = results[0]

        # Assuming your user table columns are in the order: UserId, Username, Email, FullName, RollNumber
        return User(UserId=user_data[0], Username=user_data[1], Email=user_data[2], FullName=user_data[3], RollNumber=user_data[4], PasswordHash=user_data[5])
    return None

def fetch_user_image_path(username):
    query = "SELECT ImagePath FROM Users WHERE Username = ?"
    results = db.fetch_all(query, (username,))
    if results:
        image_path_from_db = results[0][0]
        absolute_image_path = os.path.join(current_app.root_path, 'app', image_path_from_db)
        if os.path.exists(absolute_image_path):
            return absolute_image_path
        else:
            return None
    else:
        return None

def register_user(userType, status, username, department, email, full_name, password):
    existing_user_query = "SELECT COUNT(*) FROM Users WHERE Username = ?"
    user_count = db.fetch_all(existing_user_query, (username,))
    if user_count and user_count[0][0] > 0:
        flash('Username already exists. Please choose a different one.', 'error')
        return False

    userimagefolder = os.path.join(current_app.root_path, 'app/static/faces')
    if not os.path.isdir(userimagefolder):
        os.makedirs(userimagefolder)
    img_name = f"{username}_{department}.jpg"
    img_path = os.path.join(userimagefolder, img_name)

    video_capture = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    while True:
        ret, frame = video_capture.read()
        if not ret:
            break
        flipped_frame = cv2.flip(frame, 1)
        cv2.imshow('Camera', flipped_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            cv2.imwrite(img_path, flipped_frame)
            break

    video_capture.release()
    cv2.destroyAllWindows()

    sql_query = """
        INSERT INTO Users (Username, RollNumber, Email, FullName, PasswordHash, ImagePath, UserType, Status, CreatedAt) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
    """
    params = (username, department, email, full_name, password, img_path, userType, status)
    try:
        db.execute_query(sql_query, params)
        return True
    except Exception as e:
        flash('An error occurred during registration.', 'error')
        return False
