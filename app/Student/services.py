from app.util.connection import DatabaseConnection
import  face_recognition
from .models import User
from flask import current_app
import time
import cv2
import os
from flask import flash
db = DatabaseConnection()
def fetch_user_details(username):
    query = "SELECT UserId, Username, Email, FullName, RollNumber, PasswordHash FROM users WHERE Username = ? AND UserType = 'S' "
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
    print("Query results:", results)
    if results:
        image_path_from_db = results[0][0]

        # Adjust the path to include the 'app' directory
        # Note: Adjust the path as necessary based on your project structure
        absolute_image_path = os.path.join(current_app.root_path, 'app', image_path_from_db)

        # Check if the file exists
        if os.path.exists(absolute_image_path):
            return absolute_image_path
        else:
            return None
    else:
        return None

    #     # Use the actual ImagePath from the database if available
    #     image_path = results[0][0]
    #     # Construct the absolute path to verify it exists
    #     absolute_image_path = os.path.join(current_app.root_path, image_path)
    #     return absolute_image_path if os.path.exists(absolute_image_path) else None
    # else:
    #     return None
def register_user(userType, status, username, roll_no, email, full_name, password):
    existing_user_query = "SELECT COUNT(*) FROM Users WHERE Username = ?"
    db = DatabaseConnection()
    user_count = db.fetch_all(existing_user_query, (username,))
    if user_count and user_count[0][0] > 0:
        # Username already exists
        flash('Username already exists. Please choose a different one.', 'error')
        return False  # Indicate that registration was not successful

    # Capture and save the image
    userimagefolder = os.path.join(current_app.root_path, 'app/static/faces')
    if not os.path.isdir(userimagefolder):
        os.makedirs(userimagefolder)
    img_name = f"{username}_{roll_no}.jpg"
    img_path = os.path.join(userimagefolder, img_name)

    # Open the first video capture device
    video_capture = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    while True:
        ret, frame = video_capture.read()
        if not ret:
            break
        rgb_frame = frame[:, :, ::-1]
        flipped_frame = cv2.flip(frame, 1)

        # Assuming you're displaying the capture to the user with instructions
        cv2.imshow('Camera', flipped_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            cv2.imwrite(img_path, flipped_frame)
            break

    video_capture.release()
    cv2.destroyAllWindows()

    # Insert user data into the database
    sql_query = """
        INSERT INTO Users (Username, RollNumber, Email, FullName, PasswordHash, ImagePath, UserType, Status, CreatedAt) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
    """
    params = (username, roll_no, email, full_name, password, img_path, userType, status)
    try:
        db.execute_query(sql_query, params)
        return True  # Registration was successful
    except Exception as e:
        flash('An error occurred during registration.', 'error')
        return False  # Registration failed
