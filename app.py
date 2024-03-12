from flask import Flask

# #from StudentAttendance.routes import attendance_bp
# from config import Config
# from routes import setup_routes
#
# def create_app():
#     app = Flask(__name__)
#     setup_routes(app)
#     return app
#
#     # Register blueprints
#     #app.register_blueprint(attendance_bp)
#     # app.register_blueprint()
#
#
# from flask import Flask
# app = Flask(__name__)
# app.secret_key = b'\xb4\xafSp\xc3\xa8\xa0~MD\x90"\x14\xf3p\xe6\xed\xbbA\xb9\x7fC4\xd1'

def create_app():
    app = Flask(__name__)
    app.secret_key = b'\xb4\xafSp\xc3\xa8\xa0~MD\x90"\x14\xf3p\xe6\xed\xbbA\xb9\x7fC4\xd1'
    return app
