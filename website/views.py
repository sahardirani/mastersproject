from flask import Blueprint, render_template, request, flash, jsonify, url_for, redirect
from flask_login import login_required, current_user
from .models import User
from . import db, mail
import json
import datetime
from flask_mail import Mail, Message
from sqlalchemy import func
from threading import Thread

views = Blueprint('views', __name__)

# Function that only allows participants to start the interaction on the day of the interaction
def is_button_disabled():
    return False

# Index Page or homepage of the application
@views.route('/index', methods=['GET','POST'])
def index():
    if request.method == 'POST':
        return redirect(url_for('views.home'))
    else:
        return render_template('index.html', user=current_user)


# ========================================
# UPDATED - Home route with new matching system
# ========================================
@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == 'POST':
        # Read topic from the form (coming from index.html buttons)
        selected_topic = request.form.get('topic')

        if selected_topic:
            current_user.topic = selected_topic
            db.session.commit()

        # Redirect to new questionnaire instead of demographics
        return redirect(url_for('views.new_questionnaire'))
    
    if current_user.demo:
        button_disabled = is_button_disabled()
        partner = None
        
        # Check for matches using both old and new matching systems
        if current_user.haspartner:
            # First check old system (partner_id)
            if current_user.partner_id:
                partner = User.query.get(current_user.partner_id)
            else:
                # Check new matching system
                from .matching_service import MatchingService
                matches = MatchingService.get_user_matches(current_user.id, status='accepted')
                if matches:
                    match = matches[0]
                    partner_id = match.user_b_id if match.user_a_id == current_user.id else match.user_a_id
                    partner = User.query.get(partner_id)
        
        db.session.commit()
        return render_template("home.html", user=current_user, partner=partner, button_disabled=button_disabled)
    
    return render_template("home.html", user=current_user)


# ========================================
# NEW ROUTE - 15-Question Questionnaire
# ========================================
@views.route('/new_questionnaire', methods=['GET', 'POST'])
@login_required
def new_questionnaire():
    """New 15-question questionnaire with -2 to +2 scale"""
    # Import the functions from __init__.py where they are defined
    from . import save_questionnaire_responses, get_openness_category
    from .matching_service import MatchingService
    
    if request.method == 'POST':
        # Save all 15 responses
        result = save_questionnaire_responses(
            user_id=current_user.id,
            form_data=request.form
        )
        
        if result:
            openness = result['openness_score']
            category = get_openness_category(openness)
            
            if result['is_extremist']:
                flash(
                    f'Your openness score: {openness:.1f}/2.0 ({category}). '
                    'We need participants who are more open to different viewpoints. '
                    'Thank you for your interest.',
                    'error'
                )
                return redirect(url_for('views.index'))
            else:
                flash(
                    f'✓ Your openness score: {openness:.1f}/2.0 ({category}). '
                    'You are eligible for matching!',
                    'success'
                )
                
                # Mark user as registered
                current_user.demo = True
                db.session.commit()
                
                # Trigger background matching
                Thread(target=find_matches_for_user, args=(current_user.id,)).start()
                
                # Continue to existing questionnaire flow
                return redirect(url_for('views.demographics'))
        else:
            flash('Error saving responses. Please try again.', 'error')
    
    return render_template('new_questionnaire.html', user=current_user)


# ========================================
# NEW FUNCTION - Background Matching Task
# ========================================
def find_matches_for_user(user_id):
    """Background task to find matches"""
    from website import create_app
    from .matching_service import MatchingService
    
    app = create_app()
    with app.app_context():
        user = User.query.get(user_id)
        if user:
            result = MatchingService.find_best_match_for_user(user)
            if result:
                matched_user, score, decision = result
                match = MatchingService.create_match(user, matched_user, score, decision)
                
                # Update haspartner flags
                user.haspartner = True
                matched_user.haspartner = True
                
                # Set partner_id for compatibility with old system
                user.partner_id = matched_user.id
                matched_user.partner_id = user.id
                user.meeting_id = user.id
                matched_user.meeting_id = user.id
                
                db.session.commit()
                
                print(f"✓ Match created: User {user.id} <-> User {matched_user.id}, Score: {score:.2f}")
                
                # Send email notifications
                try:
                    confirmation1 = Message('Match Confirmation', sender='TolerantTogether@gmail.com')
                    confirmation2 = Message('Match Confirmation', sender='TolerantTogether@gmail.com')
                    confirmation1.add_recipient(user.email)
                    confirmation2.add_recipient(matched_user.email)
                    confirmation1.html = render_template('Email/zusage.html')
                    confirmation2.html = render_template('Email/zusage.html')
                    mail.send(confirmation1)
                    mail.send(confirmation2)
                except Exception as e:
                    print(f"Error sending email: {e}")


# ========================================
# EXISTING ROUTES - All in English
# ========================================

# Questionnaire 1, Part 1: demographic questions view
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
                flash('Please select a valid answer for each question.', category='error')
            else:
                current_user.gender = gender
                current_user.age = age
                current_user.education = education
                current_user.job = job
                db.session.commit()
                flash('Demographic data successfully processed.', category='success')
                return redirect(url_for('views.questions1'))
            
        except Exception as e:
            flash('There was an error processing the demographic data.', category='error')

    return render_template('Questionnaire1/demographics.html', user=current_user)


# Questionnaire 1, Part 2: questions on the topic
@views.route('/q1', methods=['POST', 'GET'])
@login_required
def questions1():
    if request.method == 'POST':
        try:
            # Classification is common for all topics
            current_user.classification = request.form.get('classify1')

            # Decide which questions to save based on selected topic
            topic = current_user.topic or 'climate'

            if topic == 'climate':
                current_user.climate1 = request.form.get('climate1')
                current_user.climate2 = request.form.get('climate2')
                current_user.climate3 = request.form.get('climate3')

            elif topic == 'ai_employment':
                current_user.ai_q1 = request.form.get('ai_q1')
                current_user.ai_q2 = request.form.get('ai_q2')
                current_user.ai_q3 = request.form.get('ai_q3')

            elif topic == 'freedom_speech':
                current_user.speech_q1 = request.form.get('speech_q1')
                current_user.speech_q2 = request.form.get('speech_q2')
                current_user.speech_q3 = request.form.get('speech_q3')

            # These are still common across all topics
            current_user.emotion1 = request.form.get('emotion1')
            current_user.emotion2 = request.form.get('emotion2')
            current_user.emotion3 = request.form.get('emotion3')
            current_user.future = request.form.get('future')

            db.session.commit()
            return redirect(url_for('views.questions2'))

        except Exception as e:
            flash('There was an error processing the data. Please try again.', category='error')

    return render_template('Questionnaire1/questions1.html', user=current_user)


# Questionnaire 1, Part 3: questions on the two constructs
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
            flash('Registration was successful!', category='success')
            return redirect(url_for('views.endofq1'))

        except Exception as e:
            flash('There was an error processing the data. Please try again.', category='error')

    return render_template('Questionnaire1/questions2.html', user=current_user)


# End of Questionnaire 1 page (OLD matching system - kept for backward compatibility)
@views.route('/Questionnaire1/end', methods=['GET','POST'])
@login_required
def endofq1():
    # If the user already has a partner, just show the page
    if current_user.haspartner:
        return render_template('Questionnaire1/endofq1.html', user=current_user)

    # Try to find a partner using OLD system (for backward compatibility)
    partner_query = User.query.filter(
        User.classification != None,
        User.haspartner == False,
        User.id != current_user.id,
        User.topic == current_user.topic,
        func.abs(User.classification - current_user.classification) >= 3
    )

    partner = partner_query.first()

    if partner:
        # Match them
        partner.haspartner = True
        current_user.haspartner = True
        partner.partner_id = current_user.id
        current_user.partner_id = partner.id
        current_user.meeting_id = current_user.id
        partner.meeting_id = current_user.id
        db.session.commit()

        # Send email
        try:
            confirmation1 = Message('Confirmation', sender='TolerantTogether@gmail.com')
            confirmation2 = Message('Confirmation', sender='TolerantTogether@gmail.com')
            confirmation1.add_recipient(current_user.email)
            confirmation2.add_recipient(partner.email)
            confirmation1.html = render_template('Email/zusage.html')
            confirmation2.html = render_template('Email/zusage.html')
            mail.send(confirmation1)
            mail.send(confirmation2)
        except Exception as e:
            flash('Error sending email.', category='error')

    return render_template('Questionnaire1/endofq1.html', user=current_user)
 

# View of the introduction page of the interaction 
@views.route('/Interaction/introduction', methods=['GET','POST'])
@login_required
def introduction():
    if request.method=='POST':
        return redirect(url_for('views.waitpage'))
    return render_template('Interaction/introduction.html', user=current_user)


# View of the waiting page that waits until both participants have started the interaction
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


# View of the first interaction part 
@views.route('/Interaction/climate', methods=['GET','POST'])
@login_required
def climate():
    return render_template('Interaction/climate.html', user=current_user)


# View of the second interaction part
@views.route('/Interaction/opinion', methods=['GET','POST'])
@login_required
def opinion():
    return render_template('Interaction/opinion.html', user=current_user)


# View of the third interaction part
@views.route('/Interaction/future', methods=['GET','POST'])
@login_required
def future():
    current_user.hasarrived = False
    db.session.commit()
    return render_template('Interaction/future.html', user=current_user)


# Questionnaire 2: View of perspective-taking questionnaire
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
            flash('There was an error processing the answers.', category='error')
            
    return render_template('Questionnaire2/perspective.html', user=current_user)
    

# Questionnaire 2: Perspective-Taking score view
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
        flash('There was an error calculating the score.', category='error')


# Questionnaire 2: View of the Evaluation of the interaction behaviour and the construct
@views.route('/Questionnaire2/evaluation', methods=['POST', 'GET'])
@login_required
def evaluation():
    if request.method == 'POST':
        try:
            attributes = [
                'eval11', 'eval12', 'eval13', 'eval14', 'construct12', 'construct22', 
                'construct32', 'construct42', 'construct52', 'construct62', 'construct72', 'construct82'
            ]
            
            for attr in attributes:
                setattr(current_user, attr, request.form.get(attr))

            db.session.commit()

            partner = User.query.get(current_user.partner_id)
            partner.behaviour_score = round((current_user.eval11 + current_user.eval12 + current_user.eval13)/3, 2)
            
            db.session.commit()
            
            return redirect(url_for('views.evaluation2'))
        
        except Exception as e:
            flash('There was an error processing the data.', category='error')

    return render_template('Questionnaire2/evaluation.html', user=current_user)


# Questionnaire 2: View of the evaluation of the application
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
            flash('There was an error processing the data.', category='error')

    return render_template('Questionnaire2/evaluation2.html', user=current_user)


# Questionnaire 2: View of the evaluation of the application
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
            flash('There was an error processing the data.', category='error')

    return render_template('Questionnaire2/evaluation3.html', user=current_user)


# View of final page where participant is informed about their reward
@views.route('/Reward', methods=['POST', 'GET'])
@login_required
def reward():
    partner = User.query.get(current_user.partner_id)
    try:
        if current_user.behaviour_score:
            payout = Message('Payout Information', sender='TolerantTogether@gmail.com', recipients=[current_user.email])
            payout.html = render_template('Email/auszahlung.html', user=current_user)
            mail.send(payout)

    except Exception as e:
        flash('There was an error sending the payout email. Please contact TolerantTogether@gmail.com', category='error')
        
    return render_template('Questionnaire2/reward.html', user=current_user, partner=partner)