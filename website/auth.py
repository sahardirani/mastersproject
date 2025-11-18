from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, mail
from flask_login import login_user, login_required, logout_user, current_user
from flask_mail import Message

auth = Blueprint('auth', __name__)

# Login Page logic
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            user = User.query.filter_by(email=email).first()
        except Exception:
            db.session.rollback()
            user = User.query.filter_by(email=email).first()

        try:
            if user:
                if check_password_hash(user.password, password):
                    flash('Login successfull!', category='success')
                    login_user(user, remember=True)
                    return redirect(url_for('views.home'))
                else:
                    flash('Das Passwort ist falsch, versuchen Sie es erneut.', category='error')
            else:
                flash('Unter dieser Email ist kein Nutzer registriert.', category='error')

        except Exception as e:
            # Debug output in console
            print("Login error:", e)
            flash('Es gab einen Fehler bei der Datenverarbeitung. Bitte versuchen Sie es erneut.', category='error')

    return render_template("login.html", user=current_user)


# Logout function
@auth.route('/logout')
@login_required
def logout():
    try:
        logout_user()
    except Exception as e:
        print("Logout error:", e)
        flash('Es gab einen Fehler bei ausloggen. Versuchen Sie es erneut.', category='error')

    return redirect(url_for('auth.login'))


# Sign up Page
@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        email1 = request.form.get('email1')
        user_name = request.form.get('user_name')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')

        try:
            user = User.query.filter_by(email=email).first()
        except Exception:
            db.session.rollback()
            user = User.query.filter_by(email=email).first()

        try:
            if user:
                flash('Die Email ist bereits einem Nutzer zugeordnet', category='error')
            elif len(email) < 4:
                flash('Die Email muss länger als 4 Buchstaben sein.', category='error')
            elif email != email1:
                flash('Die Emails stimmen nicht überein.', category='error')
            elif len(user_name) < 2:
                flash('Der Benutzername muss länger als zwei Buchstaben sein.', category='error')
            elif password1 != password2:
                flash('Die Passwörter stimmen nicht überein.', category='error')
            elif len(password1) < 7:
                flash('Das Passwort muss mindestens 8 Zeichen enthalten.', category='error')
            else:
                # Nutzer anlegen
                new_user = User(
                    email=email,
                    user_name=user_name,
                    password=generate_password_hash(password1)  # default = pbkdf2:sha256
                )
                db.session.add(new_user)
                db.session.commit()

                # 📧 E-MAIL AN DEN NEUEN NUTZER SENDEN
                try:
                    msg = Message(
                        subject="Tolerance Together – Registration Confirmation",
                        recipients=[email]
                    )
                    msg.body = (
                        f"Hello,\n\n"
                        f"Your account on Tolerance Together has been successfully created with the email: {email}.\n\n"
                        f"If this was NOT you, please contact us immediately at: togethertolerant@gmail.com\n\n"
                        f"Best regards,\n"
                        f"Tolerance Together Team"
                    )
                    mail.send(msg)
                except Exception as e:
                    # Nur in der Konsole melden, Registrierung nicht abbrechen
                    print("Signup email error:", e)

                login_user(new_user, remember=True)
                flash('Registrierung war erfolgreich! Bitte melden Sie sich zur Diskussion an.', category='success')
                return redirect(url_for('views.home'))

        except Exception as e:
            # Zeig den echten Fehler in der Konsole
            print("Sign-up error:", e)
            flash('Es gab einen Fehler bei der Datenverarbeitung. Bitte versuchen Sie es erneut.', category='error')

    return render_template("sign_up.html", user=current_user)
