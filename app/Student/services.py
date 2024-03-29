from app.util.connection import DatabaseConnection
import  face_recognition
from .models import User
from flask import current_app
import  pickle
import cv2
import os
from flask import flash
known_faces = []
known_names = []
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

    if results:
        image_path_from_db = results[0][0]

        image_path_from_db = os.path.normpath(image_path_from_db)

        # Note: Adjust the path as necessary based on your project structure
        absolute_image_path = os.path.join(current_app.root_path, 'app', image_path_from_db)

        # Check if the file exists
        if os.path.exists(absolute_image_path):
            user_image = face_recognition.load_image_file(absolute_image_path)
            user_encoding = face_recognition.face_encodings(user_image)[0]
            known_faces.append(user_encoding)
            known_names.append(username)
            return absolute_image_path
        else:
            return None
    else:
        return None

def register_user(user_details):
    # Extract user details
    userType = user_details.get('userType')
    status = user_details.get('status', 'pending')  # Default to 'pending' if not provided
    username = user_details['username']
    roll_no = user_details['roll_no']
    email = user_details['email']
    full_name = user_details['full_name']
    password = user_details['password']
    captured_image_path = user_details['captured_image_path']  # Ensure this is included in user_details

    db = DatabaseConnection()
    existing_user_query = "SELECT COUNT(*) FROM Users WHERE Username = ?"
    db = DatabaseConnection()
    user_count = db.fetch_all(existing_user_query, (username,))
    if user_count and user_count[0][0] > 0:
        # Username already exists
        flash('Username already exists. Please choose a different one.', 'error')
        return False  # Indicate that registration was not successful

#unnecessary steps for capturing the image using OpenCV since we have already captured the image using
    # the capture_image_from_webcam function
    # # Capture and save the image
    # userimagefolder = os.path.join(current_app.root_path, 'app/static/faces')
    # if not os.path.isdir(userimagefolder):
    #     os.makedirs(userimagefolder)
    # img_name = f"{username}_{roll_no}.jpg"
    # img_path = os.path.join(userimagefolder, img_name)
    #
    # # Open the first video capture device
    # video_capture = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    # while True:
    #     ret, frame = video_capture.read()
    #     if not ret:
    #         break
    #     rgb_frame = frame[:, :, ::-1]
    #     flipped_frame = cv2.flip(frame, 1)
    #     cv2.imshow('Capture', flipped_frame)
    #     if cv2.waitKey(1) & 0xFF == ord('q'):
    #         cv2.imwrite(img_path, flipped_frame)
    #         break
    # video_capture.release()
    # cv2.destroyAllWindows()

    # Load and check the captured image for uniqueness
    try:
        new_user_image = face_recognition.load_image_file(captured_image_path)
        new_user_encoding = face_recognition.face_encodings(new_user_image)[0]
    except IndexError:
        flash("No face detected in the image. Please try again.", "error")
        os.remove(captured_image_path)
        return False

    if not is_face_unique(new_user_encoding):
        flash('A similar face has already been registered.', 'error')
        os.remove(captured_image_path)  # Cleanup the image file as it's no longer needed
        return False


    # Insert user data into the database
    sql_query = """
        INSERT INTO Users (Username, RollNumber, Email, FullName, PasswordHash, ImagePath, UserType, Status, CreatedAt) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
    """
    params = (username, roll_no, email, full_name, password, captured_image_path, userType, status)
    try:
        db.execute_query(sql_query, params)
        return True  # Registration was successful
    except Exception as e:
        flash('An error occurred during registration.', 'error')
        os.remove(captured_image_path)
        return False  # Registration failed

def update_encodings():
    # Build the path to the 'static/faces' directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    folderModepath = os.path.join(script_dir, '..', 'static', 'faces')
    modePathList = os.listdir(folderModepath)
    print(modePathList)
    imgModeList = []
    StudentIds = []

    for path in modePathList:
        img = cv2.imread(os.path.join(folderModepath, path))
        imgModeList.append(img)
        identifier = os.path.splitext(path)[0]  # This gets the filename without the extension

        StudentIds.append(identifier)
        print(StudentIds)

    def findEncoding(imagesList):
        encodeList = []
        for img in imagesList:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            encode = face_recognition.face_encodings(img)[0]
            encodeList.append(encode)

        return encodeList

    print("Encoding Started...")
    encodeListKnown = findEncoding(imgModeList)
    encodeListKnownWithIds = [encodeListKnown, StudentIds]
    print("Encoding Complete")
    print("Current working directory:", os.getcwd())

    encode_file_path = os.path.join(script_dir, "EncodeFile.p")
    file = open(encode_file_path, 'wb')
    pickle.dump(encodeListKnownWithIds, file)
    file.close()
    print('File saved')

def is_face_unique(new_encoding, threshold=0.6):
    # Construct the path to EncodeFile.p dynamically
    encode_file_path = os.path.join(current_app.root_path, 'app', 'Student', 'EncodeFile.p')

    # Load existing encodings
    with open(encode_file_path, 'rb') as file:
        encodeListKnownWithIds = pickle.load(file)
    encodeListKnown, _ = encodeListKnownWithIds

    # Compare the new encoding with existing encodings
    for encoding in encodeListKnown:
        matches = face_recognition.compare_faces([encoding], new_encoding, tolerance=threshold)
        distance = face_recognition.face_distance([encoding], new_encoding)
        if True in matches and min(distance) < threshold:
            return False
    return True

def capture_image_from_webcam(username, roll_no):
    video_capture = cv2.VideoCapture(0)
    while True:
        ret, frame = video_capture.read()
        if not ret:
            print("Failed to grab frame")
            break
        cv2.imshow('Press Q to Capture', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            img_name = f"temp_{username}_{roll_no}.jpg"
            temp_image_path = os.path.join(current_app.root_path, 'temp', img_name)
            cv2.imwrite(temp_image_path, frame)
            print(f"Image saved as {temp_image_path}")
            break
    video_capture.release()
    cv2.destroyAllWindows()
    if 'temp_image_path' in locals():
        return temp_image_path
    else:
        raise Exception("Failed to capture image from webcam.")