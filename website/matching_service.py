from .models import UserOpinion, OpinionDimension, User, Match, db
from datetime import datetime, timedelta
from itertools import combinations  # Add this

class MatchingService:
    """Service for autonomous opposition-based user matching"""

    # Opposition score thresholds (based on 10 matching questions)
    ECHO_CHAMBER_MAX = 1.0
    IDEAL_MIN = 1.0
    IDEAL_MAX = 2.5
    EXTREME_MIN = 2.5

    @staticmethod
    def run_batch_matching(**kwargs):
        """Wrapper for the scheduler that runs the full matching process"""
        print("→ Running batch matching…")
        return MatchingService.run_matching()

    @staticmethod
    def run_matching():
        """Main matching logic - find matches for all eligible users"""
        from .models import User, Match, OpinionDimension, UserOpinion
        from . import db
        from datetime import datetime
        
        stats = {
            'users_processed': 0,
            'matches_created': 0,
            'ideal_matches': 0,
            'execution_time': 0.0,
            'errors': []
        }
        
        start_time = datetime.utcnow()
        
        try:
            # Get all eligible users
            eligible_users = User.query.filter(
                User.demo == True,
                User.is_extremist == False,
                User.haspartner == False
            ).all()
            
            stats['users_processed'] = len(eligible_users)
            
            # Group by topic
            users_by_topic = {}
            for user in eligible_users:
                if user.topic not in users_by_topic:
                    users_by_topic[user.topic] = []
                users_by_topic[user.topic].append(user)
            
            # Match within each topic
            for topic, users in users_by_topic.items():
                if len(users) < 2:
                    continue
                
                matched_pairs = MatchingService._find_optimal_matches(users, topic)
                
                for user_a, user_b, score, decision in matched_pairs:
                    match = MatchingService.create_match(user_a, user_b, score, decision)
                    if match:
                        stats['matches_created'] += 1
                        if decision == 'ideal_match':
                            stats['ideal_matches'] += 1
            
            stats['execution_time'] = (datetime.utcnow() - start_time).total_seconds()
            
        except Exception as e:
            stats['errors'].append(str(e))
            print(f"✗ Error in run_matching: {e}")
        
        return stats

    @staticmethod
    def _find_optimal_matches(users, topic):
        """Find optimal matches for a group of users"""
        from itertools import combinations
        
        potential_matches = []
        
        for user_a, user_b in combinations(users, 2):
            if user_a.haspartner or user_b.haspartner:
                continue
            
            score, decision = MatchingService.calculate_opposition_score(user_a, user_b)
            
            if decision != 'too_similar':
                potential_matches.append((user_a, user_b, score, decision))
        
        # Sort by score (highest first)
        potential_matches.sort(key=lambda x: x[2], reverse=True)
        
        # Create matches, each user only once
        used_users = set()
        final_matches = []
        
        for user_a, user_b, score, decision in potential_matches:
            if user_a.id not in used_users and user_b.id not in used_users:
                final_matches.append((user_a, user_b, score, decision))
                used_users.add(user_a.id)
                used_users.add(user_b.id)
        
        return final_matches

    @staticmethod
    def calculate_opposition_score(user_a, user_b):
        """Calculate opposition score between two users (0-4 scale)"""
        from .models import UserOpinion
        
        a_opinions = {
            op.dimension.name: op.score 
            for op in user_a.opinions 
            if op.dimension.question_type == 'matching'
        }
        b_opinions = {
            op.dimension.name: op.score 
            for op in user_b.opinions 
            if op.dimension.question_type == 'matching'
        }
        
        if not a_opinions or not b_opinions:
            return 0.0, 'too_similar'
        
        total_weighted_diff = 0.0
        total_weight = 0.0
        
        for dimension_name in a_opinions.keys():
            if dimension_name in b_opinions:
                a_score = a_opinions[dimension_name]
                b_score = b_opinions[dimension_name]
                
                dimension = next((op.dimension for op in user_a.opinions if op.dimension.name == dimension_name), None)
                if dimension:
                    weight = dimension.default_weight
                    diff = abs(a_score - b_score)
                    
                    total_weighted_diff += diff * weight
                    total_weight += weight
        
        if total_weight == 0:
            return 0.0, 'too_similar'
        
        opposition_score = (total_weighted_diff / total_weight) * 2
        
        if opposition_score < 1.0:
            decision = 'too_similar'
        elif opposition_score <= 2.5:
            decision = 'ideal_match'
        else:
            decision = 'too_extreme'
        
        return opposition_score, decision

    @staticmethod
    def create_match(user_a, user_b, opposition_score, decision):
        """Create a match between two users"""
        from .models import Match, db
        from datetime import datetime, timedelta
        
        try:
            existing = Match.query.filter(
                ((Match.user_a_id == user_a.id) & (Match.user_b_id == user_b.id)) |
                ((Match.user_a_id == user_b.id) & (Match.user_b_id == user_a.id))
            ).first()
            
            if existing:
                return existing
            
            match = Match(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                topic=user_a.topic,
                opposition_score=opposition_score,
                match_decision=decision,
                expires_at=datetime.utcnow() + timedelta(days=7)
            )
            
            db.session.add(match)
            db.session.commit()
            
            return match
            
        except Exception as e:
            print(f"✗ Error creating match: {e}")
            return None

    @staticmethod
    def get_user_matches(user_id, status=None):
        """Get all matches for a user"""
        from .models import Match
        
        query = Match.query.filter(
            ((Match.user_a_id == user_id) | (Match.user_b_id == user_id))
        )
        
        if status:
            query = query.filter_by(status=status)
        
        return query.all()

    @staticmethod
    def accept_match(match_id, user_id):
        """Accept a match"""
        from .models import Match, User, db
        from datetime import datetime
        
        match = Match.query.get(match_id)
        if not match or user_id not in [match.user_a_id, match.user_b_id]:
            return False
        
        match.status = 'accepted'
        match.last_interaction = datetime.utcnow()
        
        user_a = User.query.get(match.user_a_id)
        user_b = User.query.get(match.user_b_id)
        
        if user_a:
            user_a.haspartner = True
            user_a.partner_id = user_b.id if user_b else None
        
        if user_b:
            user_b.haspartner = True
            user_b.partner_id = user_a.id if user_a else None
        
        db.session.commit()
        return True

    @staticmethod
    def reject_match(match_id, user_id):
        """Reject a match"""
        from .models import Match, db
        
        match = Match.query.get(match_id)
        if not match or user_id not in [match.user_a_id, match.user_b_id]:
            return False
        
        match.status = 'rejected'
        db.session.commit()
        return True

    @staticmethod
    def expire_old_matches():
        """Expire matches older than 7 days"""
        from .models import Match, db
        from datetime import datetime
        
        expired = Match.query.filter(
            Match.status == 'pending',
            Match.expires_at < datetime.utcnow()
        ).all()
        
        for match in expired:
            match.status = 'expired'
        
        db.session.commit()
        return len(expired)

    @staticmethod
    def find_best_match_for_user(user):
        """Find the best match for a single user"""
        from .models import User
        
        candidates = User.query.filter(
            User.id != user.id,
            User.topic == user.topic,
            User.demo == True,
            User.is_extremist == False,
            User.haspartner == False
        ).all()
        
        if not candidates:
            return None
        
        best_match = None
        best_score = -1
        
        for candidate in candidates:
            score, decision = MatchingService.calculate_opposition_score(user, candidate)
            
            if decision == 'ideal_match' and score > best_score:
                best_match = (candidate, score, decision)
                best_score = score
        
        return best_match if best_match else None