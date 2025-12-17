from flask import render_template
from datetime import datetime, timedelta, time, date
from .models import UserOpinion, OpinionDimension, User, Match, db
from . import send_email_safe

def time_overlap(u1, u2):
    """
    Return a common time slot string if any overlap, else None.
    Cleans None and stray whitespace/newlines.
    """
    slots1 = {u1.time_slot_1, u1.time_slot_2, u1.time_slot_3}
    slots2 = {u2.time_slot_1, u2.time_slot_2, u2.time_slot_3}

    slots1 = {s.strip() for s in slots1 if s}
    slots2 = {s.strip() for s in slots2 if s}

    common = list(slots1 & slots2)
    return common[0] if common else None


class MatchingService:
    # ------------------------------------------------------------------
    # 1) Opposition score calculation using the formula
    # ------------------------------------------------------------------
    @staticmethod
    def calculate_opposition_score(user_a, user_b):
        """
        Calculate opposition score using users table columns (match1-match10)
        Formula: Opposition_Score = [∑(wi × |Ai - Bi|)] / ∑wi
        
        Returns (opposition_score, decision) where decision is one of:
        - "too_similar" (score < 1.0)
        - "ideal_match" (1.0 <= score <= 2.5)
        - "too_extreme" (score > 2.5)
        """
        weighted_diff_sum = 0.0
        total_weight = 0.0
        dimensions_used = 0
        
        # Get all matching dimensions for weights
        matching_dimensions = OpinionDimension.query.filter_by(
            question_type="matching"
        ).order_by(OpinionDimension.question_number).all()
        
        if len(matching_dimensions) != 10:
            print(f"[SCORE] Warning: Expected 10 matching dimensions, found {len(matching_dimensions)}")
            return 0.0, "too_similar"
        
        # Calculate score for each matching dimension
        for i, dimension in enumerate(matching_dimensions, 1):
            # Get scores from User model (match1-match10)
            score_a = getattr(user_a, f'match{i}', None)
            score_b = getattr(user_b, f'match{i}', None)
            
            # Skip if either score is missing
            if score_a is None or score_b is None:
                print(f"[SCORE] Missing match{i} for users {user_a.id} or {user_b.id}")
                continue
            
            try:
                score_a = float(score_a)
                score_b = float(score_b)
            except (ValueError, TypeError):
                print(f"[SCORE] Invalid score format for match{i}")
                continue
            
            # Calculate absolute difference (0-4 range)
            diff = abs(score_a - score_b)
            
            # Use dimension weight
            weight = dimension.default_weight
            
            weighted_diff_sum += weight * diff
            total_weight += weight
            dimensions_used += 1
        
        # Require at least 8 dimensions to be valid
        if dimensions_used < 8 or total_weight == 0:
            print(f"[SCORE] Insufficient data: used {dimensions_used}/10 dimensions")
            return 0.0, "too_similar"
        
        # Calculate final opposition score
        opposition_score = weighted_diff_sum / total_weight
        
        # Categorize the match
        if opposition_score < 1.0:
            decision = "too_similar"
        elif opposition_score <= 2.5:
            decision = "ideal_match"
        else:
            decision = "too_extreme"
        
        print(f"[SCORE] Users {user_a.id}-{user_b.id}: score={opposition_score:.2f}, decision={decision}")
        return opposition_score, decision

    # ------------------------------------------------------------------
    # 2) Enhanced matching: openness + opposition score + time overlap
    # ------------------------------------------------------------------
    @staticmethod
    def find_best_match_for_user(user):
        """
        Find best partner using users table columns directly
        """
        if not user.topic:
            print(f"[MATCH] User {user.id} has no topic, skipping.")
            return None
        
        if not user.demo:
            print(f"[MATCH] User {user.id} has not completed screening (demo=False), skipping.")
            return None
        
        if user.is_extremist:
            print(f"[MATCH] User {user.id} is extremist, skipping.")
            return None
        
        if user.haspartner:
            print(f"[MATCH] User {user.id} already has a partner, skipping.")
            return None
        
        if user.openness_score is None:
            print(f"[MATCH] User {user.id} has no openness_score, skipping.")
            return None
        
        # NEW: Verify user has complete matching data in users table
        matching_scores = []
        for i in range(1, 11):
            score = getattr(user, f'match{i}', None)
            if score is None:
                print(f"[MATCH] User {user.id} missing match{i}, skipping.")
                return None
            try:
                matching_scores.append(float(score))
            except (ValueError, TypeError):
                print(f"[MATCH] User {user.id} has invalid match{i} value, skipping.")
                return None
        
        # Base candidate filter (same as before)
        candidates = User.query.filter(
            User.id != user.id,
            User.topic == user.topic,
            User.demo.is_(True),
            User.is_extremist.is_(False),
            (User.haspartner.is_(False) | User.haspartner.is_(None)),
            User.openness_score.isnot(None),
        ).all()
        
        if not candidates:
            print(f"[MATCH] No candidates for user {user.id} on topic {user.topic}")
            return None
        
        # First pass: filter by quick criteria
        u_open = float(user.openness_score)
        potential_matches = []
        
        for candidate in candidates:
            # Check time overlap
            common_slot = time_overlap(user, candidate)
            if not common_slot:
                continue
            
            # NEW: Verify candidate has complete matching data
            candidate_scores = []
            valid_candidate = True
            for i in range(1, 11):
                score = getattr(candidate, f'match{i}', None)
                if score is None:
                    valid_candidate = False
                    break
                try:
                    candidate_scores.append(float(score))
                except (ValueError, TypeError):
                    valid_candidate = False
                    break
            
            if not valid_candidate:
                print(f"[MATCH] Candidate {candidate.id} missing matching data, skipping.")
                continue
            
            # Check openness compatibility
            c_open = float(candidate.openness_score)
            openness_diff = abs(u_open - c_open)
            
            potential_matches.append({
                'candidate': candidate,
                'slot': common_slot,
                'openness': c_open,
                'openness_diff': openness_diff
            })
        
        if not potential_matches:
            print(f"[MATCH] No candidates with overlapping time slots for user {user.id}")
            return None
        
        # Third pass: calculate opposition scores for valid candidates
        best_candidate = None
        best_score = None
        best_slot = None
        best_opposition_score = None
        best_decision = None
        
        for match_data in potential_matches:
            candidate = match_data['candidate']
            common_slot = match_data['slot']
            c_open = match_data['openness']
            openness_diff = match_data['openness_diff']
            
            # Calculate opposition score (now uses users table)
            opposition_score, decision = MatchingService.calculate_opposition_score(user, candidate)
            
            # Only consider ideal matches
            if decision != "ideal_match":
                print(f"[MATCH] Candidate {candidate.id} excluded: {decision} (score={opposition_score:.2f})")
                continue
            
            # Calculate composite compatibility score
            avg_openness = (u_open + c_open) / 2.0
            opposition_quality = 1.0 - abs(opposition_score - 1.75) / 0.75
            openness_compatibility = max(0, 2.0 - openness_diff)
            
            compatibility = (
                opposition_quality * 3.0 +
                openness_compatibility * 2.0 +
                avg_openness * 0.5
            )
            
            if (best_candidate is None) or (compatibility > best_score):
                best_candidate = candidate
                best_score = compatibility
                best_slot = common_slot
                best_opposition_score = opposition_score
                best_decision = decision
        
        if not best_candidate:
            print(f"[MATCH] No suitable candidate with ideal opposition score for user {user.id}")
            return None
        
        print(f"[MATCH] Found match: {user.id} <-> {best_candidate.id}, opposition={best_opposition_score:.2f}, decision={best_decision}, compatibility={best_score:.2f}, slot={best_slot}")
        return best_candidate, best_opposition_score, best_decision, best_slot

    # ------------------------------------------------------------------
    # 3) Create a Match row
    # ------------------------------------------------------------------
    @staticmethod
    def create_match(user_a, user_b, opposition_score, decision, common_slot=None):
        if not user_a or not user_b:
            return None
        if user_a.id == user_b.id:
            return None
        
        match = Match(
            user_a_id=user_a.id,
            user_b_id=user_b.id,
            topic=user_a.topic or user_b.topic,
            opposition_score=opposition_score,
            match_decision=decision,
            scheduled_time_slot=common_slot,
            status="accepted",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=14),
        )

        db.session.add(match)
        db.session.commit()
        print(f"[MATCH] Created match {match.id}")
        return match

    # ------------------------------------------------------------------
    # 4) Batch matching for scheduler
    # ------------------------------------------------------------------
    @staticmethod
    def run_batch_matching(**kwargs):
        stats = {
            "users_processed": 0,
            "matches_created": 0,
            "topics_processed": 0,
            "ideal_matches": 0,
            "excluded_too_similar": 0,
            "excluded_too_extreme": 0,
        }
        
        eligible_users = User.query.filter(
            User.demo.is_(True),
            User.is_extremist.is_(False),
            (User.haspartner.is_(False) | User.haspartner.is_(None)),
            User.openness_score.isnot(None),
            User.topic.isnot(None),
        ).all()
        
        stats["users_processed"] = len(eligible_users)
        
        topics = set()
        for user in eligible_users:
            topics.add(user.topic)
            
            if user.haspartner:
                continue
            
            # Verify user has matching data
            missing_data = []
            for i in range(1, 11):
                if getattr(user, f'match{i}', None) is None:
                    missing_data.append(f'match{i}')
            
            if missing_data:
                print(f"[BATCH] User {user.id} missing {missing_data}, skipping")
                continue
            
            result = MatchingService.find_best_match_for_user(user)
            if not result:
                continue
            
            partner, opposition_score, decision, slot = result
            
            if partner.haspartner:
                continue
            
            # Create match (with openness_score fix)
            try:
                match = MatchingService.create_match(user, partner, opposition_score, decision, slot)
                
                # Update user flags
                user.haspartner = True
                partner.haspartner = True
                user.partner_id = partner.id
                partner.partner_id = user.id
                user.meeting_id = user.id
                partner.meeting_id = user.id
                
                # Send emails...
                db.session.commit()
                stats["matches_created"] += 1
                
                if decision == "ideal_match":
                    stats["ideal_matches"] += 1
                    
            except Exception as e:
                print(f"[BATCH] ERROR creating match: {e}")
                db.session.rollback()
        
        stats["topics_processed"] = len(topics)
        print(f"[BATCH] users={stats['users_processed']}, matches_created={stats['matches_created']}, ideal_matches={stats['ideal_matches']}")
        return stats

    # ------------------------------------------------------------------
    # 5) Read matches for a user
    # ------------------------------------------------------------------
    @staticmethod
    def get_user_matches(user_id, status=None):
        """Get matches where the given user participates."""
        query = Match.query.filter(
            (Match.user_a_id == user_id) | (Match.user_b_id == user_id)
        )
        if status:
            query = query.filter(Match.status == status)
        return query.order_by(Match.created_at.desc()).all()

    # ------------------------------------------------------------------
    # 6) Accept / reject
    # ------------------------------------------------------------------
    @staticmethod
    def accept_match(match_id, user_id):
        """Mark a match as accepted."""
        match = Match.query.get(match_id)
        if not match or user_id not in [match.user_a_id, match.user_b_id]:
            return False

        match.status = "accepted"

        user_a = User.query.get(match.user_a_id)
        user_b = User.query.get(match.user_b_id)

        if user_a and user_b:
            user_a.haspartner = True
            user_b.haspartner = True
            user_a.partner_id = user_b.id
            user_b.partner_id = user_a.id
            user_a.meeting_id = user_a.id
            user_b.meeting_id = user_a.id

        db.session.commit()
        return True

    @staticmethod
    def reject_match(match_id, user_id):
        """Reject a match."""
        match = Match.query.get(match_id)
        if not match or user_id not in [match.user_a_id, match.user_b_id]:
            return False

        match.status = "rejected"
        db.session.commit()
        return True

    # ------------------------------------------------------------------
    # 7) Expire old matches
    # ------------------------------------------------------------------
    @staticmethod
    def expire_old_matches():
        """Expire matches whose expires_at is in the past."""
        now = datetime.utcnow()
        old_matches = Match.query.filter(
            Match.status == "pending",
            Match.expires_at.isnot(None),
            Match.expires_at < now,
        ).all()

        count = 0
        for match in old_matches:
            match.status = "expired"
            count += 1

        if count > 0:
            db.session.commit()

        return count