from flask import Blueprint, render_template, request, flash, jsonify, url_for, redirect, session
from flask_login import login_required, current_user
from .models import User
from . import db, mail
import json
import datetime
from flask_mail import Mail, Message
from sqlalchemy import func
from threading import Thread  # NEW: for background matching

views = Blueprint('views', __name__)


# function that only allows participants to start the interaction on the day of the interaction
def is_button_disabled():
    # current_time = datetime.datetime.now()
    # target_time = datetime.datetime(2023, 7, 12, 13, 0, 0)  

    # if current_time < target_time:
    #     return True
    # else:
    return False


# Index Page or homepage of the application
@views.route('/index', methods=['GET','POST'])
def index():
    if request.method == 'POST':
        topic = request.form.get("topic")
        return redirect(url_for('views.home'))
    else:
        return render_template('index.html', user=current_user)


# Theme home page view that is dependent upon having completed the first questionnaire
# and upon being assigned to an interaction partner
@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == 'POST':
        # read topic from the form (coming from index.html buttons)
        selected_topic = request.form.get('topic')

        if selected_topic:
            current_user.topic = selected_topic
            db.session.commit()

        # NEW: after saving topic, go to new 15-question questionnaire first
        return redirect(url_for('views.new_questionnaire_part1'))

    
    if current_user.demo:
        button_disabled = is_button_disabled()
        partner = None
        if current_user.haspartner:
            # OLD SYSTEM: use partner_id if present
            partner = User.query.get(current_user.partner_id)

            # OPTIONAL NEW SYSTEM FALLBACK: if no partner found but user is marked as having a partner,
            # try to look up matches via MatchingService
            if not partner:
                try:
                    from .matching_service import MatchingService
                    matches = MatchingService.get_user_matches(current_user.id, status='accepted')
                    if matches:
                        match = matches[0]
                        partner_id = match.user_b_id if match.user_a_id == current_user.id else match.user_a_id
                        partner = User.query.get(partner_id)
                except Exception:
                    pass
        
        db.session.commit()
        return render_template("home.html", user=current_user, partner=partner, button_disabled=button_disabled)
    
    return render_template("home.html", user=current_user)

@views.route('/new_questionnaire/part1', methods=['GET', 'POST'])
@login_required
def new_questionnaire_part1():
    if request.method == 'POST':
        # store attitude1–5 temporarily in the session
        for i in range(1, 6):
            key = f'attitude{i}'
            session[key] = request.form.get(key)
        # go to part B
        return redirect(url_for('views.new_questionnaire'))

    # template with only the first 5 questions
    return render_template('new_questionnaire_part1.html', user=current_user)

# ========================================
# NEW ROUTE - 15-Question Questionnaire
# ========================================
@views.route('/new_questionnaire', methods=['GET', 'POST'])
@login_required
def new_questionnaire():
    from . import save_questionnaire_responses, get_openness_category
    from .matching_service import MatchingService

    if request.method == 'POST':
        # 1) Collect attitude1–5 from the session (Part A)
        combined_data = {}
        for i in range(1, 6):
            key = f'attitude{i}'
            if key in session:
                combined_data[key] = session[key]

        # 2) Add all Part B fields (match1–10) from this form
        combined_data.update(request.form.to_dict())

        # 3) Save all 15 responses together
        result = save_questionnaire_responses(
            user_id=current_user.id,
            form_data=combined_data
        )

        if result:
            openness = result['openness_score']
            category = get_openness_category(openness)

            if result['is_extremist']:
                # Kind message, no score shown
                flash(
                    'Thank you very much for taking the time to complete the questionnaire. '
                    'Unfortunately, based on your answers, you do not meet the eligibility criteria for this study. '
                    'We are sorry for not inviting you to a dialogue session.',
                    'error'
                )
                return redirect(url_for('views.index'))
            else:
                # Neutral / positive message, no score shown
                flash(
                    'Thank you for completing the questionnaire. '
                    'Your responses have been successfully recorded and you are eligible to continue in the study.',
                    'success'
                )

                current_user.demo = True
                db.session.commit()

                # after both parts → demographics
                return redirect(url_for('views.demographics'))
        else:
            flash('An error occurred while saving your answers. Please try again.', 'error')

    # GET: show only Part B (match1–10)
    return render_template('new_questionnaire_part2.html', user=current_user)

# ========================================
# NEW FUNCTION - Background Matching Task
# ========================================
# def find_matches_for_user(user_id):
#     """Background task to find matches using MatchingService"""
#     # from website import create_app
#     from .matching_service import MatchingService
    
#     app = create_app()
#     with app.app_context():
#         user = User.query.get(user_id)
#         if user:
#             result = MatchingService.find_best_match_for_user(user)
#             if result:
#                 matched_user, score, decision, common_slot = result
#                 match = MatchingService.create_match(
#                     user, 
#                     matched_user, 
#                     score, 
#                     decision, 
#                     common_slot
#                 )
                
#                 # Update haspartner flags
#                 user.haspartner = True
#                 matched_user.haspartner = True
                
#                 # Set partner_id for compatibility with old system
#                 user.partner_id = matched_user.id
#                 matched_user.partner_id = user.id
#                 user.meeting_id = user.id
#                 matched_user.meeting_id = user.id
                
#                 db.session.commit()
                
#                 print(f"✓ Match created: User {user.id} <-> User {matched_user.id}, Score: {score:.2f}")
                
#                 # Send email notifications
#                 try:
#                     confirmation1 = Message('Zusage', sender='TolerantTogether@gmail.com')
#                     confirmation2 = Message('Zusage', sender='TolerantTogether@gmail.com')
#                     confirmation1.add_recipient(user.email)
#                     confirmation2.add_recipient(matched_user.email)
#                     confirmation1.html = render_template('Email/zusage.html')
#                     confirmation2.html = render_template('Email/zusage.html')
#                     mail.send(confirmation1)
#                     mail.send(confirmation2)
#                 except Exception as e:
#                     print(f"Error sending email: {e}")
def find_matches_for_user(user_id):
    """Find matches for a user using the existing app/db context"""
    from .matching_service import MatchingService

    user = User.query.get(user_id)
    if not user:
        print(f"[MATCH] User {user_id} not found")
        return

    # Step 1: find best match
    result = MatchingService.find_best_match_for_user(user)
    if not result:
        print(f"[MATCH] No suitable match found for user {user.id}")
        return

    matched_user, score, decision, common_slot = result

    # Step 2: create match record
    match = MatchingService.create_match(
        user,
        matched_user,
        score,
        decision,
        common_slot,
    )

    # Step 3: update both users
    user.haspartner = True
    matched_user.haspartner = True
    user.partner_id = matched_user.id
    matched_user.partner_id = user.id
    user.meeting_id = user.id
    matched_user.meeting_id = user.id

    db.session.commit()

    print(f"✓ Match created: User {user.id} <-> User {matched_user.id}, "
          f"Score: {score:.2f}, Slot: {common_slot}")



# Questionnaire 1, Part 1: demographic questions view
# Writing of submitted answers into database
@views.route('/demographics', methods=['POST', 'GET'])
@login_required
def demographics():
    if request.method == 'POST':
        try:
            gender = request.form.get('gender')
            age = request.form.get('age')
            education = request.form.get('education')
            job = request.form.get('job')

            # 2） Availability slots (NEW)
            slot1 = request.form.get('availability1')
            slot2 = request.form.get('availability2')
            slot3 = request.form.get('availability3')
            
            if (
                not gender or not age or not education or not job
                or not slot1  # at least one slot must be selected
            ):
                flash('Please select a valid answer for each question..', category='error')
            else:
                current_user.gender = gender
                current_user.age = age
                current_user.education = education
                current_user.job = job

# 5） Save availability slots
                current_user.time_slot_1 = slot1
                current_user.time_slot_2 = slot2
                current_user.time_slot_3 = slot3

                db.session.commit()
                flash('Demographic Data  Daten was saved successfully.', category='success')
                
                find_matches_for_user(current_user.id)


                return redirect(url_for('views.endofq1'))

            
        except Exception as e:
            flash('There was an error in the processing of the demographic data.', category='error')

    return render_template('Questionnaire1/demographics.html', user=current_user)


# Questionnaire 1, Part 2: questions on the topic
# Writing of submitted answers into database
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
# Writing of submitted answers into database
@views.route('/Questionnaire1/q2', methods=['GET','POST'])
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


# End of Questionnaire 1 page
# On this page the matching of conversation partners takes place
# The system goes through the list of participants and searches for a partner with a different opinion and who is not assigned to another user
@views.route('/Questionnaire1/end', methods=['GET','POST'])
@login_required
def endofq1():
    # If the user already has a partner, just show the page
    return render_template('Questionnaire1/endofq1.html', user=current_user)
# @login_required
# def endofq1():
#     # If the user already has a partner, just show the page
#     if current_user.haspartner:
#         return render_template('Questionnaire1/endofq1.html', user=current_user)

#     # Try to find a partner
#     partner_query = User.query.filter(
#         User.classification != None,
#         User.haspartner == False,
#         User.id != current_user.id,
#         User.topic == current_user.topic,
#         func.abs(User.classification - current_user.classification) >= 3
#     )

#     partner = partner_query.first()

#     if partner:
#         # Match them
#         partner.haspartner = True
#         current_user.haspartner = True
#         partner.partner_id = current_user.id
#         current_user.partner_id = partner.id
#         current_user.meeting_id = current_user.id
#         partner.meeting_id = current_user.id
#         db.session.commit()

#         # Try email
#         try:
#             zusage1 = Message('Zusage', sender='TolerantTogether@gmail.com')
#             zusage2 = Message('Zusage', sender='TolerantTogether@gmail.com')
#             zusage1.add_recipient(current_user.email)
#             zusage2.add_recipient(partner.email)
#             zusage1.html = render_template('Email/zusage.html')
#             zusage2.html = render_template('Email/zusage.html')
#             mail.send(zusage1)
#             mail.send(zusage2)
#         except Exception as e:
#             flash('Error sending the e-mail.', category='error')

#     return render_template('Questionnaire1/endofq1.html', user=current_user)
 

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
        
        # TESTING MODE: Add "?test=1" to URL to bypass waiting
        is_test_mode = request.args.get('test') == '4'
        
        if request.method=='POST':
            # Simulate partner arrival in test mode
            if is_test_mode or partner.hasarrived:
                return 'partner_arrived'
            else:
                return 'no_partner_arrived'
        else:
            # In test mode, also mark partner as arrived immediately
            if is_test_mode and partner:
                partner.hasarrived = True
                db.session.commit()
                
            return render_template('Interaction/waitPage.html', user=current_user, test_mode=is_test_mode)
        
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
    db.session.commit()  # add this line
    return render_template('Interaction/future.html', user=current_user)

@views.route('/Questionnaire2/perspective', methods=['GET', 'POST'])
@login_required
def perspective_questionnaire():
    if request.method == 'POST':
        try:
            # Save the new post-discussion experience answers
            fields = [
                'post_confident',
                'post_open_listen',
                'post_shared_understanding',
                'post_respectful',
                'post_comfortable',
                'post_learned',
                'post_listened',
                'post_deep_think',
                'post_participate_again',
                'post_reflection',
            ]
            for field in fields:
                setattr(current_user, field, request.form.get(field))

            db.session.commit()

            # After this questionnaire → go directly to evaluation2 (no score page)
            return redirect(url_for('views.evaluation2'))

        except Exception as e:
            flash('There was an error saving your answers. Please try again.', category='error')

    # GET → just show the questionnaire
    return render_template('Questionnaire2/perspective.html', user=current_user)

# Questionnaire 2: Perspective-Taking score view
# Calculation of perspective score
@views.route('/Questionnaire2/score', methods=['POST', 'GET'])
@login_required
def score():
    # Score page disabled – always forward into the remaining questionnaire
    return redirect(url_for('views.evaluation2'))


# Questionnaire 2: View of the Evaluation of the interaction behaviour and the construct
# Writing of submitted answers into database
@views.route('/Questionnaire2/evaluation', methods=['POST', 'GET'])
@login_required
def evaluation():
    if request.method == 'POST':
        try:
            # Store the 10 post-discussion responses
            for i in range(1, 11):
                field_name = f'match_post{i}'
                value = request.form.get(field_name)
                setattr(current_user, field_name, value)

            db.session.commit()
            
            # Optional: Calculate opinion change
            opinion_change = calculate_opinion_change(current_user)
            
            return redirect(url_for('views.evaluation2'))
        
        except Exception as e:
            flash('There was an error processing the data..', category='error')

    return render_template('Questionnaire2/evaluation.html', user=current_user)


def calculate_opinion_change(user):
    """Calculate the change in opinions before and after discussion"""
    total_change = 0
    for i in range(1, 11):
        pre = getattr(user, f'match{i}', 0) or 0
        post = getattr(user, f'match_post{i}', 0) or 0
        total_change += abs(post - pre)
    
    avg_change = total_change / 10
    return round(avg_change, 2)

# Questionnaire 2: View of the evaluation of the application
# Writing of submitted answers into database
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
# Writing of submitted answers into database
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
            flash('There was an error processing the data..', category='error')
            # Handle the exception or log the error if needed

    return render_template('Questionnaire2/evaluation3.html', user=current_user)


# View of final page where participant is informed about his reward
# Automated email containing information on paying process
@views.route('/Reward', methods=['POST', 'GET'])
@login_required
def reward():
    return render_template('Questionnaire2/reward.html', user=current_user)
