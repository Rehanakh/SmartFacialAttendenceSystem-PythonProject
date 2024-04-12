from app.util.connection import DatabaseConnection
import  face_recognition
from .models import User
from flask import current_app
import  pickle
import cv2
import os
from flask import flash
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
known_faces = []
known_names = []
db = DatabaseConnection()
def fetch_user_details(username):
    query = "SELECT UserId, Username, Email, FullName, RollNumber, PasswordHash FROM users WHERE Username = ? AND UserType = 'S' AND Status='Approved'"
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

def get_attendance_records(student_id,course_id=None, page=1, per_page=10):
    db = DatabaseConnection()
    offset = (page - 1) * per_page
    query = """
        SELECT a.attendance_date, c.course_name,a.session_id, CONVERT(VARCHAR, cs.start_time, 108) + ' - ' + CONVERT(VARCHAR, cs.end_time, 108) AS session_time, 
         a.status FROM Attendance a
        JOIN Courses c ON a.course_id = c.course_id
        JOIN CourseSessions cs ON a.session_id = cs.session_id WHERE a.student_id = ?
    """
    params = [student_id]

    if course_id:
        query += " AND a.course_id = ?"
        params.append(course_id)

    query += " ORDER BY a.attendance_date DESC"
    query += " OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
    params.extend([offset, per_page])

    records = db.fetch_all(query, params)
    # Assuming total_records query is implemented
    total_records_query = """
            SELECT COUNT(*)
            FROM Attendance a
            WHERE a.student_id = ?
        """
    total_records_params = [student_id]
    if course_id:
        total_records_query += " AND a.course_id = ?"
        total_records_params.append(course_id)
    total_records = db.fetch_all(total_records_query, total_records_params)[0][0]

    return records, total_records

def get_attendance_summary(student_id):
    query = """
    SELECT status, COUNT(*) as count
    FROM Attendance
    WHERE student_id = %s
    GROUP BY status
    """
    from app.util.connection import DatabaseConnection
    import face_recognition
    from .models import User
    from flask import current_app
    import pickle
    import cv2
    import os
    from flask import flash
    known_faces = []
    known_names = []
    db = DatabaseConnection()

    def fetch_user_details(username):
        query = "SELECT UserId, Username, Email, FullName, RollNumber, PasswordHash FROM users WHERE Username = ? AND UserType = 'S' AND Status='Approved'"
        db = DatabaseConnection()
        results = db.fetch_all(query, (username,))
        if results:
            user_data = results[0]

            # Assuming your user table columns are in the order: UserId, Username, Email, FullName, RollNumber
            return User(UserId=user_data[0], Username=user_data[1], Email=user_data[2], FullName=user_data[3],
                        RollNumber=user_data[4], PasswordHash=user_data[5])
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

        # unnecessary steps for capturing the image using OpenCV since we have already captured the image using
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

    def get_attendance_records(student_id, course_id=None, page=1, per_page=10):
        db = DatabaseConnection()
        offset = (page - 1) * per_page
        query = """
            SELECT a.attendance_date, c.course_name,a.session_id, CONVERT(VARCHAR, cs.start_time, 108) + ' - ' + CONVERT(VARCHAR, cs.end_time, 108) AS session_time, 
             a.status FROM Attendance a
            JOIN Courses c ON a.course_id = c.course_id
            JOIN CourseSessions cs ON a.session_id = cs.session_id WHERE a.student_id = ?
        """
        params = [student_id]

        if course_id:
            query += " AND a.course_id = ?"
            params.append(course_id)

        query += " ORDER BY a.attendance_date DESC"
        query += " OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        params.extend([offset, per_page])

        records = db.fetch_all(query, params)
        # Assuming total_records query is implemented
        total_records_query = """
                SELECT COUNT(*)
                FROM Attendance a
                WHERE a.student_id = ?
            """
        total_records_params = [student_id]
        if course_id:
            total_records_query += " AND a.course_id = ?"
            total_records_params.append(course_id)
        total_records = db.fetch_all(total_records_query, total_records_params)[0][0]

        return records, total_records

def get_attendance_data(student_id):
    query = """
           SELECT status, COUNT(*) as count
           FROM Attendance
           WHERE student_id = ?
           GROUP BY status
           """
    params = (student_id,)
    results = db.fetch_all(query, params)
    return results

def get_attendance_trends_with_courses(student_id):
    query = """
    SELECT A.attendance_date, A.status, COUNT(*) AS count, C.course_name,C.course_id
    FROM Attendance A
    JOIN Courses C ON A.course_id = C.course_id
    WHERE A.student_id = ?
    GROUP BY A.attendance_date, A.status,  C.course_name,C.course_id
    ORDER BY A.attendance_date
    """
    params = (student_id,)
    results = db.fetch_all(query, params)
    return results

# def train_model():
#     db = DatabaseConnection()
#     query = """
#     SELECT s.student_id, s.course_id, s.participation_score, s.assignment_completion_score, s.test_score, a.status
#     FROM Scores s
#     left JOIN Attendance a ON s.student_id = a.student_id AND s.course_id = a.course_id
#     """
#     df = pd.read_sql(query, db)
#     df['at_risk'] = (df['test_score'] < 70) | (df['status'] == 'Absent')
#
#     features = df[['participation_score', 'assignment_completion_score', 'test_score']]
#     labels = df['at_risk']
#
#     X_train, X_test, y_train, y_test = train_test_split(features, labels, test_size=0.2, random_state=42)
#
#     model = RandomForestClassifier()
#     model.fit(X_train, y_train)
#     return model

def get_aggregated_scores(student_id):
    query = """
        SELECT course_id, AVG(test_score) AS avg_test_score, AVG(participation_score) AS avg_participation_score, AVG(assignment_completion_score) AS avg_assignment_score
        FROM Scores
        WHERE student_id = ?
        GROUP BY course_id
    """
    params = (student_id,)
    aggregated_scores = db.fetch_all(query, params)
    return aggregated_scores

def get_attendance_summary(student_id):
    query = """
        SELECT course_id, status, COUNT(status) AS status_count
        FROM Attendance
        WHERE student_id = ?
        GROUP BY course_id, status
    """
    params = (student_id,)
    attendance_summary = db.fetch_all(query, params)
    return attendance_summary

def predict_risk(student_id):
    scores = get_aggregated_scores(student_id)
    attendance = get_attendance_summary(student_id)

    if not scores or not attendance:
        return "Data Unavailable"

    try:
        scores_list = [list(score) for score in scores]  # Convert each tuple to a list
        scores_df = pd.DataFrame(scores_list, columns=['course_id', 'avg_test_score', 'avg_participation_score', 'avg_assignment_score'])

        attendance_list = [list(attendance_tuple) for attendance_tuple in attendance]
        attendance_df = pd.DataFrame(attendance_list, columns=['course_id', 'status', 'status_count'])

        # Aggregate attendance data by course and status
        attendance_agg = attendance_df.groupby(['course_id', 'status']).agg({'status_count': 'sum'}).reset_index()
        # Pivot the aggregated attendance data to have one row per course with columns for each status
        attendance_pivot = attendance_agg.pivot(index='course_id', columns='status', values='status_count').fillna(
            0).reset_index()

        # Assuming 'Present' status is an indicator of attendance, calculate an average based on some criterion
        # Here we just use 'Present' count directly as 'avg_attendance_score' for simplicity
        attendance_pivot['avg_attendance_score'] = attendance_pivot['Present']  # Adjust this calculation as needed

        # Merge the scores and calculated attendance scores
        combined_df = pd.merge(scores_df, attendance_pivot, on='course_id', how='left')


        # combined_df['absent_rate'] = combined_df.apply(
        #     lambda row: row['status_count'] if row['status'] == 'Absent' else 0, axis=1)
        # combined_df['at_risk'] = combined_df.apply(lambda row: row['avg_test_score'] < 70 or row['absent_rate'] > 3,
        #                                            axis=1)

        # Calculate the overall average score
        combined_df['overall_avg_score'] = combined_df[
            ['avg_test_score', 'avg_participation_score', 'avg_assignment_score', 'avg_attendance_score']].mean(axis=1)

        # Determine risk status
        combined_df['at_risk'] = combined_df.apply( lambda row: row['overall_avg_score'] < 70 or row.get('Absent', 0) > 3 or row.get('Late', 0) > 5, axis=1)
        risk_status = "At Risk" if combined_df['at_risk'].any() else "Not At Risk"

        return risk_status
    except ValueError as e:
        print("ValueError occurred:", e)
        return "Error"

    except KeyError as e:
        print("KeyError occurred:", e)
        return "Error"

    except Exception as e:
        print("Unexpected error occurred:", e)
        return "Error"
