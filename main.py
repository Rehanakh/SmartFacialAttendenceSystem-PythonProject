from flask import Flask
from config import Config


from app.Student.routes import student_setup_routes
from app.Admin.routes import admin_setup_routes
app = Flask(__name__,template_folder='app/templates', static_folder='app/static')
app.secret_key = b'\xb4\xafSp\xc3\xa8\xa0~MD\x90"\x14\xf3p\xe6\xed\xbbA\xb9\x7fC4\xd1'
app.config.from_object(Config)

# Register routes with the app instance


student_setup_routes(app)
admin_setup_routes(app)
if __name__ == '__main__':
    app.run(debug=True)