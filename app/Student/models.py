from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
class User:
    def __init__(self, UserId, Username, Email, FullName, RollNumber, PasswordHash):
        self.UserId = UserId
        self.Username = Username
        self.Email = Email
        self.FullName = FullName
        self.RollNumber = RollNumber
        self.PasswordHash = PasswordHash

class CourseSession(db.Model):
    __tablename__ = 'course_sessions'
    session_id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    day_of_week = db.Column(db.String(10), nullable=False)
    session_date = db.Column(db.Date, nullable=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
