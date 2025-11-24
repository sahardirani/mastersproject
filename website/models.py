from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
from datetime import datetime  # ADD THIS IMPORT


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

    topic = db.Column(db.String(100))  # Already exists ✓

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

    haspartner = db.Column(db.Boolean, default=False)  # Already exists ✓
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

        # Post-discussion experience questionnaire (after the discussion)
    post_confident = db.Column(db.Integer)              # I felt confident expressing my opinion
    post_open_listen = db.Column(db.Integer)            # I was open to listening...
    post_shared_understanding = db.Column(db.Integer)   # I believe it is possible to find shared understanding
    post_respectful = db.Column(db.Integer)             # The discussion was respectful and constructive
    post_comfortable = db.Column(db.Integer)            # I felt comfortable sharing my thoughts
    post_learned = db.Column(db.Integer)                # I learned something new
    post_listened = db.Column(db.Integer)               # I felt listened to and understood
    post_deep_think = db.Column(db.Integer)             # The discussion encouraged me to think more deeply
    post_participate_again = db.Column(db.Integer)      # I would participate in a similar discussion again
    post_reflection = db.Column(db.Text)                # Additional reflections

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

    eval11 = db.Column(db.Integer)
    eval12 = db.Column(db.Integer) 
    eval13 = db.Column(db.Integer)
    eval14 = db.Column(db.Integer)

    # PRE-DISCUSSION opinion responses (from new_questionnaire_part2.html)
    match1 = db.Column(db.Integer)
    match2 = db.Column(db.Integer)
    match3 = db.Column(db.Integer)
    match4 = db.Column(db.Integer)
    match5 = db.Column(db.Integer)
    match6 = db.Column(db.Integer)
    match7 = db.Column(db.Integer)
    match8 = db.Column(db.Integer)
    match9 = db.Column(db.Integer)
    match10 = db.Column(db.Integer)

    # POST-DISCUSSION opinion responses (same questions, after discussion)
    match_post1 = db.Column(db.Integer)
    match_post2 = db.Column(db.Integer)
    match_post3 = db.Column(db.Integer)
    match_post4 = db.Column(db.Integer)
    match_post5 = db.Column(db.Integer)
    match_post6 = db.Column(db.Integer)
    match_post7 = db.Column(db.Integer)
    match_post8 = db.Column(db.Integer)
    match_post9 = db.Column(db.Integer)
    match_post10 = db.Column(db.Integer)

    eval3 = db.Column(db.Integer)
    feedback = db.Column(db.String(500))

    
    construct = db.Column(db.String(500))
    perspective = db.Column(db.String(500))
    
    # ========================================
    # ADD THESE NEW FIELDS FOR MATCHING SYSTEM
    # ========================================
    openness_score = db.Column(db.Float, nullable=True)  # NEW
    is_extremist = db.Column(db.Boolean, default=False)  # NEW
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # NEW
    
    # NEW RELATIONSHIPS - Add these at the end
    opinions = db.relationship('UserOpinion', back_populates='user', cascade='all, delete-orphan')
    matches_initiated = db.relationship('Match', foreign_keys='Match.user_a_id', back_populates='user_a', cascade='all, delete-orphan')
    matches_received = db.relationship('Match', foreign_keys='Match.user_b_id', back_populates='user_b', cascade='all, delete-orphan')

    # Availability for up to three time slots
    time_slot_1 = db.Column(db.String(50), nullable=True)
    time_slot_2 = db.Column(db.String(50), nullable=True)
    time_slot_3 = db.Column(db.String(50), nullable=True)


# ========================================
# ADD THESE NEW MODELS AT THE END OF THE FILE
# ========================================

class OpinionDimension(db.Model):
    """
    Defines the 15 opinion dimensions:
    - 5 General Attitude questions (for screening)
    - 10 Topic-Specific questions (for matching algorithm)
    """
    __tablename__ = 'opinion_dimensions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    display_name = db.Column(db.String(200), nullable=False)
    question_type = db.Column(db.String(50))  # 'attitude' or 'matching'
    question_number = db.Column(db.Integer)  # 1-5 for attitude, 1-10 for matching
    description = db.Column(db.Text)
    default_weight = db.Column(db.Float, default=1.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user_opinions = db.relationship('UserOpinion', back_populates='dimension', cascade='all, delete-orphan')


class UserOpinion(db.Model):
    """
    Stores user's response to each question
    Scale: -2 to +2 (5-point scale, no conversion needed)
    """
    __tablename__ = 'user_opinions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    dimension_id = db.Column(db.Integer, db.ForeignKey('opinion_dimensions.id'), nullable=False)
    
    # Score from questionnaire: -2 to +2 scale (already normalized)
    score = db.Column(db.Float, nullable=False)
    
    # Custom weight for this user (overrides dimension default if set)
    custom_weight = db.Column(db.Float, nullable=True)
    
    # Metadata
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='opinions')
    dimension = db.relationship('OpinionDimension', back_populates='user_opinions')
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('user_id', 'dimension_id', name='unique_user_dimension'),
        db.CheckConstraint('score >= -2 AND score <= 2', name='check_score_range'),
    )
    
    @property
    def effective_weight(self):
        """Get the effective weight (custom or default)"""
        return self.custom_weight if self.custom_weight is not None else self.dimension.default_weight


class Match(db.Model):
    """Stores matching results between users"""
    __tablename__ = 'matches'
    
    id = db.Column(db.Integer, primary_key=True)
    user_a_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_b_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Topic they're matched on
    topic = db.Column(db.String(50), nullable=False)
    
    # Opposition score (calculated from 10 matching questions only)
    opposition_score = db.Column(db.Float, nullable=False)
    match_decision = db.Column(db.String(50), nullable=False)  # 'ideal_match', 'too_similar', 'too_extreme'
    
    scheduled_time_slot = db.Column(db.String(50), nullable=True)

    # Openness compatibility (both users are open-minded)
    both_open_minded = db.Column(db.Boolean, default=True)
    
    # Match status
    status = db.Column(db.String(50), default='pending')  # pending, accepted, rejected, expired
    
    # Interaction tracking
    conversation_started = db.Column(db.Boolean, default=False)
    last_interaction = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user_a = db.relationship('User', foreign_keys=[user_a_id], back_populates='matches_initiated')
    user_b = db.relationship('User', foreign_keys=[user_b_id], back_populates='matches_received')
    
    # Constraints
    __table_args__ = (
        db.CheckConstraint('user_a_id != user_b_id', name='check_different_users'),
        db.CheckConstraint('opposition_score >= 0 AND opposition_score <= 4', name='check_score_range'),
    )
    
    @property
    def is_ideal_match(self):
        """Check if this is an ideal match"""
        return self.match_decision == 'ideal_match'
    
    @property
    def is_active(self):
        """Check if match is still active"""
        if self.status not in ['pending', 'accepted']:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True


class MatchHistory(db.Model):
    """Tracks historical matching data for analytics"""
    __tablename__ = 'match_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    matched_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic = db.Column(db.String(50), nullable=False)
    opposition_score = db.Column(db.Float, nullable=False)
    match_decision = db.Column(db.String(50), nullable=False)
    
    # Outcome tracking
    accepted = db.Column(db.Boolean, nullable=True)
    conversation_count = db.Column(db.Integer, default=0)
    total_interaction_time = db.Column(db.Integer, default=0)  # in minutes
    
    # Feedback
    user_rating = db.Column(db.Integer, nullable=True)  # 1-5 stars
    user_feedback = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)


class MatchingSession(db.Model):
    """Tracks batch matching sessions for analytics"""
    __tablename__ = 'matching_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_type = db.Column(db.String(50), default='automated')  # automated, manual
    topic = db.Column(db.String(50))  # Which topic was matched
    
    # Statistics
    total_users_processed = db.Column(db.Integer, default=0)
    total_matches_created = db.Column(db.Integer, default=0)
    ideal_matches_count = db.Column(db.Integer, default=0)
    extremists_excluded = db.Column(db.Integer, default=0)
    
    # Performance
    execution_time = db.Column(db.Float)  # in seconds
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Optional: store configuration
    config_json = db.Column(db.JSON, nullable=True)