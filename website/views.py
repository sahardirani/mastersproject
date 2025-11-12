from flask import Blueprint, render_template, request, flash, jsonify, url_for, redirect
from flask_login import login_required, current_user
from .models import User
from . import db, mail
import json
import datetime
from flask_mail import Mail, Message
from sqlalchemy import func

views = Blueprint('views', __name__)

#function that only allows participants to start the interaction on the day of the interaction
def is_button_disabled():
    current_time = datetime.datetime.now()
    target_time = datetime.datetime(2023, 7, 12, 13, 0, 0)  

    if current_time < target_time:
        return True
    else:
        return False

#Index Page or homepage of the application
@views.route('/index', methods=['GET','POST'])
def index():
    if request.method == 'POST':
        return redirect(url_for('views.home'))
    else:
        return render_template('index.html', user=current_user)

#Theme home page view that is dependent upon having completed the first questionnaire
#and upon being assigned to an interaction partner
@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == 'POST':
        return redirect(url_for('views.demographics'))
    
    if current_user.demo:
        button_disabled = is_button_disabled()
        partner = None
        if current_user.haspartner:
            partner = User.query.get(current_user.partner_id)
        
        db.session.commit()
        return render_template("home.html", user=current_user, partner=partner, button_disabled=button_disabled)
    
    return render_template("home.html", user=current_user)

#Questionnaire 1, Part 1: demographic questions view
#Writing of submitted answers into database
@views.route('/demographics', methods=['POST', 'GET'])
@login_required
def demographics():
    if request.method == 'POST':
        try:
            gender = request.form.get('gender')
            age = request.form.get('age')
            education = request.form.get('education')
            job = request.form.get('job')
            
            if not gender or not age or not education or not job:
                flash('Bitte wähle für jede Frage eine gültige Antwort.', category='error')
            else:
                current_user.gender = gender
                current_user.age = age
                current_user.education = education
                current_user.job = job
                db.session.commit()
                flash('Demographische Daten wurden erfolgreich verarbeitet.', category='success')
                return redirect(url_for('views.questions1'))
            
        except Exception as e:
            flash('Es gab einen Fehler bei der Verarbeitung der demographischen Daten.', category='error')

    return render_template('Questionnaire1/demographics.html', user=current_user)

#Questionnaire 1, Part 2: questions on the topic
#Writing of submitted answers into database
@views.route('/q1', methods=['POST', 'GET'])
@login_required
def questions1():
    if request.method == 'POST':
        try:
            current_user.classification = request.form.get('classify1')
            current_user.climate1 = request.form.get('climate1')
            current_user.climate2 = request.form.get('climate2')
            current_user.climate3 = request.form.get('climate3')
            current_user.emotion1 = request.form.get('emotion1')
            current_user.emotion2 = request.form.get('emotion2')
            current_user.emotion3 = request.form.get('emotion3')
            current_user.future = request.form.get('future')
            
            db.session.commit()
            return redirect(url_for('views.questions2'))

        except Exception as e:
            flash('Es gab einen Fehler bei der Verarbeitung der Daten. Versuchen Sie es erneut', category='error')

    return render_template('Questionnaire1/questions1.html', user=current_user)

#Questionnaire 1, Part 3: questions on the two constructs
#Writing of submitted answers into database
@views.route('Questionnaire1/q2', methods=['GET','POST'])
@login_required
def questions2():
    if request.method == 'POST':
        try:
            current_user.construct1 = request.form.get('construct1')
            current_user.construct2 = request.form.get('construct2')
            current_user.construct3 = request.form.get('construct3')
            current_user.construct4 = request.form.get('construct4')
            current_user.construct5 = request.form.get('construct5')
            current_user.construct6 = request.form.get('construct6')
            current_user.construct7 = request.form.get('construct7')
            current_user.construct8 = request.form.get('construct8')
            current_user.demo = True
            db.session.commit()
            flash('Anmeldung war erfolgreich!', category='success')
            return redirect(url_for('views.endofq1'))

        except Exception as e:
            flash('Es gab einen Fehler bei der Verarbeitung der Daten. Versuchen Sie es erneut', category='error')

    return render_template('Questionnaire1/questions2.html', user=current_user)

#End of Questionnaire 1 page
#On this page the matching of conversation partners takes place
#The system goes through the list of participants and searches for a partner with a different opinion and who is not assigned to another user
@views.route('/Questionnaire1/end', methods=['GET','POST'])
@login_required
def endofq1():
    if current_user.haspartner:
        return render_template('Questionnaire1/endofq1.html', user=current_user)
    elif User.query.filter(User.classification != None, func.abs(User.classification - current_user.classification) >= 3, User.haspartner == False).count() >= 1:
        partner = User.query.filter(User.classification != None, User.haspartner == False, User.id!=current_user.id).first()
        partner.haspartner = True
        current_user.haspartner = True
        partner.partner_id = current_user.id
        current_user.partner_id = partner.id
        current_user.meeting_id = current_user.id
        partner.meeting_id = current_user.id
        db.session.commit()

        try:
            zusage1 = Message('Zusage', sender='TolerantTogether@gmail.com')
            zusage2 = Message('Zusage', sender='TolerantTogether@gmail.com')
            zusage1.add_recipient(current_user.email)
            zusage2.add_recipient(partner.email)
            zusage1.html = render_template('Email/zusage.html')
            zusage2.html = render_template('Emial/zusage.html')
            mail.send(zusage1)
            mail.send(zusage2)
        except Exception as e:
            flash('Es gab einen Fehler beim Versenden der Benachrichtigungs E-Mail in der sie alle weiteren Informationen erhalten. Bitte Kontaktieren Sie TolerantTogether@gmail.com', category='error')

    return render_template('Questionnaire1/endofq1.html', user=current_user)
    

#View of the introduction page of the interaction 
@views.route('/Interaction/introduction', methods=['GET','POST'])
@login_required
def introduction():
    if request.method=='POST':
        return redirect(url_for('views.waitpage'))
    return render_template('Interaction/introduction.html', user=current_user)

#View of the waiting page that waits until both participants have started the interaction
@views.route('/Interaction/WaitingPage', methods=['GET','POST'])
@login_required
def waitpage():
    try:
        partner = User.query.get(current_user.partner_id)
        current_user.hasarrived = True
        db.session.commit()
        if request.method=='POST':
            if partner.hasarrived:
                return 'partner_arrived'
            else:
                return 'no_partner_arrived'
        else:
            return render_template('Interaction/waitPage.html', user=current_user)
        
    except Exception as e:
        return render_template('Interaction/waitPage.html', user=current_user)

#View of the first interaction part 
@views.route('/Interaction/climate', methods=['GET','POST'])
@login_required
def climate():
    return render_template('Interaction/climate.html', user=current_user)

#View of the second interaction part
@views.route('/Interaction/opinion', methods=['GET','POST'])
@login_required
def opinion():
    return render_template('Interaction/opinion.html', user=current_user)

#View of the third interaction part
@views.route('/Interaction/future', methods=['GET','POST'])
@login_required
def future():
    current_user.hasarrived = False
    return render_template('Interaction/future.html', user=current_user)

#Questionnaire 2: View of perspective-taking questionnaire
#Wirting of answers into database
@views.route('/Questionnaire2/perspective', methods=['POST', 'GET'])
@login_required
def perspective():
        if request.method == 'POST':
            try:
                current_user.classification_p = request.form.get('classify_p1')
                current_user.climate_p1 = request.form.get('climate_p1')
                current_user.climate_p2 = request.form.get('climate_p2')
                current_user.climate_p3 = request.form.get('climate_p3')
                current_user.emotion_p1 = request.form.get('emotion_p1')
                current_user.emotion_p2 = request.form.get('emotion_p2')
                current_user.emotion_p3 = request.form.get('emotion_p3')
                current_user.future_p = request.form.get('future_p')
            
                db.session.commit()
                return redirect(url_for('views.score'))
            
            except Exception as e:
                flash('Es gab einen Fehler bei der Verarbeitung der Antworten.', category='error')
                # Handle the exception or log the error if needed
                
        return render_template('Questionnaire2/perspective.html', user=current_user)
    

#Questionnaire 2: Perspective-Taking score view
#Calculation of perspective score
@views.route('/Questionnaire2/score', methods=['POST', 'GET'])
@login_required
def score():
    try:
        if request.method == 'POST':
            return redirect(url_for('views.evaluation'))
        else:
            partner = User.query.get(current_user.partner_id)

            cla = abs(current_user.classification_p - partner.classification)
            c1 = abs(current_user.climate_p1 - partner.climate1)
            c2 = abs(current_user.climate_p2 - partner.climate2)
            c3 = abs(current_user.climate_p3 - partner.climate3)
            e1 = abs(current_user.emotion_p1 - partner.emotion1)
            e2 = abs(current_user.emotion_p2 - partner.emotion2)
            e3 = abs(current_user.emotion_p3 - partner.emotion3)
            f = abs(current_user.future_p - partner.future)
            score = round(((48 - (cla + c1 + c2 + c3 + e1 + e2 + e3 + f)) / 48) * 100, 2)
            
            current_user.perspective_score = score

            db.session.commit()

            return render_template('Questionnaire2/score.html', user=current_user, score=score)

    except Exception as e:
        flash('Es gab einen Fehler bei der Berechnung des Scores.', category='error')
        # Handle the exception or log the error if needed


#Questionnaire 2: View of the Evaluation of the interaction behaviour and the construct
#Writing of submitted answers into database
@views.route('/Questionnaire2/evaluation', methods=['POST', 'GET'])
@login_required
def evaluation():
    if request.method == 'POST':
        try:
            attributes = [
                'eval11', 'eval12', 'eval13', 'eval14', 'construct12', 'construct22', 'construct32', 'construct42', 'construct52', 'construct62', 'construct72', 'construct82'
            ]
            
            for attr in attributes:
                setattr(current_user, attr, request.form.get(attr))

            db.session.commit()

            partner = User.query.get(current_user.partner_id)
            partner.behaviour_score = round((current_user.eval11 + current_user.eval12 + current_user.eval13)/3, 2)
            
            db.session.commit()
            
            return redirect(url_for('views.evaluation2'))
        
        except Exception as e:
            flash('Es gab einen Fehler bei der Verarbeitung der Daten.', category='error')
            # Handle the exception or log the error if needed

    return render_template('Questionnaire2/evaluation.html', user=current_user)

#Questionnaire 2: View of the evaluation of the application
#Writing of submitted answers into database
@views.route('/Questionnaire2/evaluation2', methods=['POST', 'GET'])
@login_required
def evaluation2():
    if request.method == 'POST':
        try:
            attributes = [
                'ueq1', 'ueq2', 'ueq3', 'ueq4', 'ueq5', 'ueq6', 'ueq7', 'ueq8'
            ]
            
            for attr in attributes:
                setattr(current_user, attr, request.form.get(attr))

            db.session.commit()

            return redirect(url_for('views.evaluation3'))
        except Exception as e:
            flash('Es gab einen Fehler bei der Verarbeitung der Daten.', category='error')

    return render_template('Questionnaire2/evaluation2.html', user=current_user)


#Questionnaire 2: View of the evaluation of the application
#Writing of submitted answers into database
@views.route('/Questionnaire2/evaluation3', methods=['POST', 'GET'])
@login_required
def evaluation3():
    if request.method == 'POST':
        try:
            attributes = [
                'eval3', 'feedback', 'perspective', 'construct'
            ]
            
            for attr in attributes:
                setattr(current_user, attr, request.form.get(attr))
            
            db.session.commit()
            
            return redirect(url_for('views.reward'))
        
        except Exception as e:
            flash('Es gab einen Fehler bei der Verarbeitung der Daten.', category='error')
            # Handle the exception or log the error if needed

    return render_template('Questionnaire2/evaluation3.html', user=current_user)

#View of final page where participant is informed about his reward
#Automated email containing information on paying process
@views.route('/Reward', methods=['POST', 'GET'])
@login_required
def reward():
    partner = User.query.get(current_user.partner_id)
    try:
        if current_user.behaviour_score:
            auszahlung = Message('Auszahlung', sender='TolerantTogether@gmail.com', recipients=[current_user.email])
            auszahlung.html = render_template('Email/auszahlung.html', user=current_user)
            mail.send(auszahlung)


    except Exception as e:
        flash('Es gab einen Fehler beim Versenden der E-Mail bezüglich der Auszahlung. Bitte Kontaktieren Sie TolerantTogether@gmail.com', category='error')
        
    return render_template('Questionnaire2/reward.html', user=current_user, partner=partner)

