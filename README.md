# pythonproject
Smart Attendance system:
This project is an Attendance Management System designed to automate the attendance process for educational institutions. It consists of three main modules: The Student Module, the Professor Module and the Admin Module. The system is built using the Flask framework for Python, leveraging face recognition technology to mark attendance based on students' faces.

1.Student Module:
- Allows students to register 
- After registration. Allow students to login once registration approved.
- Utilized Flask-Mail for email operations, enabling seamless integration with SMTP servers for sending emails.
- Implemented an OTP-based email verification system for new user registrations.
- Added automatic welcome email functionality upon successful registration and OTP verification. 
- Enables students to view their attendance records.
- Utilizes face recognition for marking attendance automatically during classes.
- Implemented emotion detection functionality while marking attendance
- Students can enroll in the courses
- Students can remove the courses from the enrolled list
- Student can view attendance history of own 


Each module has its route.py and a common connection.py for database connection.
TestCases are attached under testCase folder for each page: Home,Login,registration,Student etc
1.1:COurse

Admin Module
Provides functionalities for admin users to manage student records.
Allows the creation and management of courses and sessions.
Enables admins to view and export attendance reports for different courses and sessions.
 