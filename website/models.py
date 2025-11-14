from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func



class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(500))
    user_name = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
    family_name = db.Column(db.String(150))
    demo = db.Column(db.Boolean, default=False)
    gender = db.Column(db.String(100))
    age = db.Column(db.String(100))
    education = db.Column(db.String(100))
    job = db.Column(db.String(100)) 

    topic = db.Column(db.String(100))  # 'climate', 'ai_employment', 'freedom_speech'

    classification = db.Column(db.Integer)

    climate1 = db.Column(db.Integer)
    climate2 = db.Column(db.Integer)
    climate3 = db.Column(db.Integer)

    ai_q1 = db.Column(db.Integer)
    ai_q2 = db.Column(db.Integer)
    ai_q3 = db.Column(db.Integer)

    speech_q1 = db.Column(db.Integer)
    speech_q2 = db.Column(db.Integer)
    speech_q3 = db.Column(db.Integer)
    
    emotion1 = db.Column(db.Integer)
    emotion2 = db.Column(db.Integer)
    emotion3 = db.Column(db.Integer)
    future = db.Column(db.Integer)
    
    construct1 = db.Column(db.Integer)
    construct2 = db.Column(db.Integer)
    construct3 = db.Column(db.Integer)
    construct4 = db.Column(db.Integer)
    construct5 = db.Column(db.Integer)
    construct6 = db.Column(db.Integer)
    construct7 = db.Column(db.Integer)
    construct8 = db.Column(db.Integer)

    haspartner = db.Column(db.Boolean, default=False)
    partner_id = db.Column(db.Integer)
    meeting_id = db.Column(db.Integer)
    hasarrived = db.Column(db.Boolean, default=False)
    perspective_score = db.Column(db.Float)
    behaviour_score = db.Column(db.Float)
    paypal = db.Column(db.Boolean, default=False)

    classification_p = db.Column(db.Integer)
    climate_p1 = db.Column(db.Integer)
    climate_p2 = db.Column(db.Integer)
    climate_p3 = db.Column(db.Integer)
    emotion_p1 = db.Column(db.Integer)
    emotion_p2 = db.Column(db.Integer)
    emotion_p3 = db.Column(db.Integer)
    future_p = db.Column(db.Integer)

    construct12 = db.Column(db.Integer)
    construct22 = db.Column(db.Integer)
    construct32 = db.Column(db.Integer)
    construct42 = db.Column(db.Integer)
    construct52 = db.Column(db.Integer)
    construct62 = db.Column(db.Integer)
    construct72 = db.Column(db.Integer)
    construct82 = db.Column(db.Integer)

    ueq1 = db.Column(db.Integer)
    ueq2 = db.Column(db.Integer)
    ueq3 = db.Column(db.Integer)
    ueq4 = db.Column(db.Integer)
    ueq5 = db.Column(db.Integer)
    ueq6 = db.Column(db.Integer)
    ueq7 = db.Column(db.Integer)
    ueq8 = db.Column(db.Integer)

    eval11 = db.Column(db.Integer)
    eval12 = db.Column(db.Integer) 
    eval13 = db.Column(db.Integer)
    eval14 = db.Column(db.Integer)

    eval3 = db.Column(db.Integer)
    feedback = db.Column(db.String(500))
    construct = db.Column(db.String(500))
    perspective = db.Column(db.String(500))
    
