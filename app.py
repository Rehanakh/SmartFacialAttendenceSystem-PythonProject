from flask import Flask
def create_app():
    app = Flask(__name__)
    app.secret_key = b'\xb4\xafSp\xc3\xa8\xa0~MD\x90"\x14\xf3p\xe6\xed\xbbA\xb9\x7fC4\xd1'
    return app
