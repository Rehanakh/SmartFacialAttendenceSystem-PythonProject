from flask import Flask
from config import Config
from flask_mail import Mail
import os

# Flask-Mail configuration
def setup_mail(app):
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'nshkhan123@gmail.com'
    app.config['MAIL_PASSWORD'] = 'rzhm xaqr jaye fegk'
    app.config['MAIL_DEFAULT_SENDER'] = 'nshkhan123@gmail.com'

    # app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
    # app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    # app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ('true', '1', 't')
    # app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    # app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    # app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')
    mail = Mail(app)
    return mail


from app.Student.routes import student_setup_routes
from app.Admin.routes import admin_setup_routes
app = Flask(__name__,template_folder='app/templates', static_folder='app/static')
app.secret_key = b'\xb4\xafSp\xc3\xa8\xa0~MD\x90"\x14\xf3p\xe6\xed\xbbA\xb9\x7fC4\xd1'
app.config.from_object(Config)

# Setup mail
mail = setup_mail(app)

# Register routes with the app instance
student_setup_routes(app)
admin_setup_routes(app)
if __name__ == '__main__':
    app.run(debug=True)