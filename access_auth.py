import hashlib
from . import app
from .forms import ResetPasswordForm
from .mongoflask import MongoJSONEncoder, ObjectIdConverter
from flask import Flask, jsonify, request, json, url_for, render_template, flash, redirect
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, BadSignature, BadData
from flask_pymongo import PyMongo 
from bson.objectid import ObjectId 
from datetime import datetime 
from flask_bcrypt import Bcrypt 
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_jwt_extended import create_access_token

mail = Mail(app)

s = URLSafeTimedSerializer(app.config["SECRET_KEY"])
mongo = PyMongo(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

CORS(app)

# user register endpoint
@app.route("/api/users/register", methods=["POST"])
def register():
    users = mongo.db.users 
    firstName = request.get_json()["firstName"]
    lastName = request.get_json()["lastName"]
    email = request.get_json()["email"]
    phone = str(request.get_json()["phone"])
    address = str(request.get_json()["address"])
    password = bcrypt.generate_password_hash(request.get_json()["password"]).decode("utf-8")
    created = datetime.utcnow()
    uid = str(int(hashlib.md5((firstName + lastName + email + phone).encode("utf-8")).hexdigest(), 16))[0:6] ### unique user id

    # verify user exist
    existing_user = users.find_one({"email": email})

    # update db with user data
    if existing_user is None:
        user_id = users.insert({
        "firstName": firstName,
        "lastName": lastName,
        "email": email,
        "password": password,
        "phone": phone,
        "address": address,
        "created": created,
        "uid": uid,
        "emailConfirm": False
    })
    
        new_user = users.find_one({"_id": user_id})

        result = jsonify({
            "message": new_user["email"] + " registered and activation link sent to your email"
            }), 201
        
        # user confirmation email with activation url logic here
        token = s.dumps(email, salt="email-confirm")
        msg = Message("Confirm Email", sender="admin@test.com", recipients=[email])
        link = url_for("confirm_email", token=token, _external=True)
        msg.body = render_template("confirm_mail.html", token=token, link=link, firstName=new_user["firstName"])
        mail.send(msg)
    else:
        result = jsonify({"message": "user already exists!"}), 403
    return result


# activation link url prefix
@app.route("/api/users/register/confirm_email/<token>")
def confirm_email(token):
    # logic to validate token and confirm user
    try:
        email = s.loads(token, salt="email-confirm", max_age=3600)
        users = mongo.db.users

        # update emailConfirm when user clicks activation link
        users.find_one_and_update(
            {"email": email},
            {"$set":
                {"emailConfirm": True}
            },upsert=False
        )
    except BadSignature as e:
        if e.payload is not None:
            try:
                decoded_payload = s.load_payload(e.payload)
            except BadData:
                pass
        flash("The token is expired or invalid.", "danger")
        return redirect(url_for("user_login"))
    flash("Your email is confirmed and account activated! Please login to continue", "success")
    return redirect(url_for("user_login"))

# user login endpoint
@app.route("/api/users/login", methods=["POST"])
def login():
    users = mongo.db.users 
    email = request.get_json()["email"]
    password = request.get_json()["password"]
    result = ""

    response = users.find_one({"email": email})

    # multiple logic to verify user exists, confirmed and password valid
    if response:
        if response["emailConfirm"] == True:
            if bcrypt.check_password_hash(response["password"], password):
                access_token = create_access_token(identity = {
                    "firstName": response["firstName"],
                    "lastName": response["lastName"],
                    "email": response["email"]
                })
                result = jsonify({
                    "token": access_token,
                    "firstName": response["firstName"],
                    "lastName": response["lastName"],
                    "user_id": response["_id"]
                    })
            else:
                result = jsonify({"message": "Invalid username/password"}), 401
        else:
            result = jsonify({"message": "email/account not yet confirmed"}), 401
    else:
        result = jsonify({"message": "No results found"}), 403
    return result

# user reset password begins here
@app.route("/api/users/reset_password", methods=["GET", "POST"])
def reset_password():
    users = mongo.db.users
    email = request.get_json()["email"]
    user_exist = users.find_one({"email": email})

    # verify user and send reset link/token
    if user_exist:
        token = s.dumps(email, salt="reset-password-salt")
        msg = Message("Password Reset", sender="admin@test.com", recipients=[email])
        link = url_for("reset_token", token=token, _external=True)
        msg.body = render_template("password_mail.html", token=token, link=link, email=email) 
        mail.send(msg)
        result = jsonify({"message": "password reset link has been sent to your email"})
    else: 
        result = jsonify({"message": "this user does not exist"}), 400
    return result

### password reset headache starts here ###
@app.route("/api/users/password_reset/<token>", methods=["GET", "POST"])
def reset_token(token):
    try:
        email = s.loads(token, salt="reset-password-salt", max_age=3600)
        # This payload is decoded and safe
    except BadSignature as e:
        if e.payload is not None:
            try:
                decoded_payload = s.load_payload(e.payload)
            except BadData:
                pass
        flash("The token is expired or invalid.", "danger")
        return redirect(url_for("user_login"))
    # import form to collect new password and update db with new pass
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode("utf-8")
        users = mongo.db.users
        users.find_one_and_update(
            {"email": email},
            {"$set":
                {"password": hashed_password}
            },upsert=False
        )
        flash("Your password has been updated! You are now able to log in.", "success")
        return redirect(url_for("user_login"))
    return render_template("reset_token.html", title="Reset Password", form=form)

@app.route("/")
@app.route("/login")
def user_login():
    return render_template("login.html")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")