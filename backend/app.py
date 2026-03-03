"""
STRATEX - Flask Backend Entry Point
"""

from flask import Flask

app = Flask(__name__)

# TODO: Register blueprints / routes

if __name__ == "__main__":
    app.run(debug=True, port=5000)
