from flask import Flask, send_from_directory
import os

app = Flask(__name__)

with app.test_request_context('/'):
    try:
        r = send_from_directory(os.path.expanduser('~/Documents/certs-pdf'), 'CAN-BUS-ECU-TUNING_course-cert.pdf')
        print(r.status)
    except Exception as e:
        print("Error:", e)
