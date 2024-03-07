# config.py
import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or b'\xb4\xafSp\xc3\xa8\xa0~MD\x90"\x14\xf3p\xe6\xed\xbbA\xb9\x7fC4\xd1'


    PERMANENT_SESSION_LIFETIME = timedelta(minutes=20)

