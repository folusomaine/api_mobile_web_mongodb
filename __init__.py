import os
from flask import Flask  # Import the Flask class
app = Flask(__name__)    # Create an instance of the class for our use

app.config.from_pyfile('config.cfg')ss