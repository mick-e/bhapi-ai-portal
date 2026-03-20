"""Unit tests for social risk detection models."""

import pytest

from src.moderation.social_risk import (
    SocialRiskCategory,
    SocialRiskClassifier,
    SocialRiskResult,
    classify_social_risk,
)

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def classifier():
    return SocialRiskClassifier()


# ---------------------------------------------------------------------------
# Grooming pattern tests
# ---------------------------------------------------------------------------


class TestGroomingPatterns:
    def test_flattery_pattern(self, classifier):
        result = classifier.classify("you're so special to me")
        assert result.category == SocialRiskCategory.GROOMING
        assert "flattery" in result.matched_patterns
        assert result.risk_score >= 15

    def test_secrecy_pattern_dont_tell(self, classifier):
        result = classifier.classify("don't tell anyone about this")
        assert result.category == SocialRiskCategory.GROOMING
        assert "secrecy" in result.matched_patterns
        assert result.risk_score >= 25

    def test_secrecy_pattern_our_secret(self, classifier):
        result = classifier.classify("this is our secret okay")
        assert result.category == SocialRiskCategory.GROOMING
        assert "secrecy" in result.matched_patterns

    def test_secrecy_pattern_keep_between_us(self, classifier):
        result = classifier.classify("keep this between us")
        assert result.category == SocialRiskCategory.GROOMING
        assert "secrecy" in result.matched_patterns

    def test_info_solicitation_address(self, classifier):
        result = classifier.classify("send me your address please")
        assert result.category == SocialRiskCategory.GROOMING
        assert "info_solicitation" in result.matched_patterns

    def test_info_solicitation_where_live(self, classifier):
        result = classifier.classify("where do you live?")
        assert result.category == SocialRiskCategory.GROOMING
        assert "info_solicitation" in result.matched_patterns

    def test_info_solicitation_school(self, classifier):
        result = classifier.classify("what school do you go to?")
        assert result.category == SocialRiskCategory.GROOMING
        assert "info_solicitation" in result.matched_patterns

    def test_info_solicitation_buy(self, classifier):
        result = classifier.classify("i'll buy you a new phone")
        assert result.category == SocialRiskCategory.GROOMING
        assert "info_solicitation" in result.matched_patterns

    def test_isolation_meet_alone(self, classifier):
        result = classifier.classify("let's meet me alone after school")
        assert result.category == SocialRiskCategory.GROOMING
        assert "isolation" in result.matched_patterns
        assert result.risk_score >= 30

    def test_isolation_come_to_my(self, classifier):
        result = classifier.classify("come to my house this weekend")
        assert result.category == SocialRiskCategory.GROOMING
        assert "isolation" in result.matched_patterns

    def test_trust_building(self, classifier):
        result = classifier.classify("you can trust me, I'm different")
        assert result.category == SocialRiskCategory.GROOMING
        assert "trust_building" in result.matched_patterns

    def test_age_minimizing_just_a_number(self, classifier):
        result = classifier.classify("age is just a number, right?")
        assert result.category == SocialRiskCategory.GROOMING
        assert "age_minimizing" in result.matched_patterns
        assert result.risk_score >= 30

    def test_age_minimizing_mature_for_age(self, classifier):
        result = classifier.classify("you're so mature for your age")
        assert result.category == SocialRiskCategory.GROOMING
        assert "age_minimizing" in result.matched_patterns

    def test_multiple_grooming_patterns(self, classifier):
        result = classifier.classify(
            "you're so special, don't tell your parents. let's meet up alone"
        )
        assert result.category == SocialRiskCategory.GROOMING
        assert len(result.matched_patterns) >= 3
        assert result.severity == "critical"


# ---------------------------------------------------------------------------
# Cyberbullying pattern tests
# ---------------------------------------------------------------------------


class TestBullyingPatterns:
    def test_exclusion_nobody_likes(self, classifier):
        result = classifier.classify("nobody likes you at school")
        assert result.category == SocialRiskCategory.CYBERBULLYING
        assert "exclusion" in result.matched_patterns

    def test_exclusion_everyone_hates(self, classifier):
        result = classifier.classify("everyone hates you")
        assert result.category == SocialRiskCategory.CYBERBULLYING
        assert "exclusion" in result.matched_patterns

    def test_death_threat_kys(self, classifier):
        result = classifier.classify("just kys already")
        assert result.category == SocialRiskCategory.CYBERBULLYING
        assert "death_threat" in result.matched_patterns
        assert result.severity in ("critical", "high")

    def test_death_threat_go_die(self, classifier):
        result = classifier.classify("go die in a fire")
        assert result.category == SocialRiskCategory.CYBERBULLYING
        assert "death_threat" in result.matched_patterns

    def test_threat_hurt_you(self, classifier):
        result = classifier.classify("I'll hurt you if you tell anyone")
        assert result.category == SocialRiskCategory.CYBERBULLYING
        assert "threat" in result.matched_patterns

    def test_threat_watch_your_back(self, classifier):
        result = classifier.classify("watch your back tomorrow")
        assert result.category == SocialRiskCategory.CYBERBULLYING
        assert "threat" in result.matched_patterns

    def test_derogatory_ugly(self, classifier):
        result = classifier.classify("you're ugly and everyone knows it")
        assert result.category == SocialRiskCategory.CYBERBULLYING
        assert "derogatory" in result.matched_patterns

    def test_derogatory_stupid(self, classifier):
        result = classifier.classify("you're stupid, go away")
        assert result.category == SocialRiskCategory.CYBERBULLYING
        assert "derogatory" in result.matched_patterns

    def test_dismissal_shut_up(self, classifier):
        result = classifier.classify("shut up, no one cares")
        assert result.category == SocialRiskCategory.CYBERBULLYING
        assert "dismissal" in result.matched_patterns

    def test_dismissal_not_invited(self, classifier):
        result = classifier.classify("you're not invited to the party")
        assert result.category == SocialRiskCategory.CYBERBULLYING
        assert "dismissal" in result.matched_patterns

    def test_multiple_bullying_patterns(self, classifier):
        result = classifier.classify(
            "nobody likes you, you're ugly, go die"
        )
        assert result.category == SocialRiskCategory.CYBERBULLYING
        assert len(result.matched_patterns) >= 3
        assert result.severity == "critical"


# ---------------------------------------------------------------------------
# Sexting pattern tests
# ---------------------------------------------------------------------------


class TestSextingPatterns:
    def test_image_request_send_pic(self, classifier):
        result = classifier.classify("send me a pic of yourself")
        assert result.category == SocialRiskCategory.SEXTING
        assert "image_request" in result.matched_patterns

    def test_image_request_show_me(self, classifier):
        result = classifier.classify("show me your face on camera")
        assert result.category == SocialRiskCategory.SEXTING
        assert "image_request" in result.matched_patterns

    def test_explicit_request_take_off(self, classifier):
        result = classifier.classify("take off your shirt")
        assert result.category == SocialRiskCategory.SEXTING
        assert "explicit_request" in result.matched_patterns
        assert result.risk_score >= 35

    def test_explicit_request_naked(self, classifier):
        result = classifier.classify("are you naked right now?")
        assert result.category == SocialRiskCategory.SEXTING
        assert "explicit_request" in result.matched_patterns

    def test_pressure_loved_me(self, classifier):
        result = classifier.classify("if you loved me you would do this")
        assert result.category == SocialRiskCategory.SEXTING
        assert "pressure" in result.matched_patterns

    def test_pressure_everyone_does_it(self, classifier):
        result = classifier.classify("everyone does it, it's no big deal")
        assert result.category == SocialRiskCategory.SEXTING
        assert "pressure" in result.matched_patterns

    def test_body_reference(self, classifier):
        result = classifier.classify("tell me about your body")
        assert result.category == SocialRiskCategory.SEXTING
        assert "body_reference" in result.matched_patterns

    def test_multiple_sexting_patterns(self, classifier):
        result = classifier.classify(
            "send me a pic, take off your clothes, everyone does it"
        )
        assert result.category == SocialRiskCategory.SEXTING
        assert len(result.matched_patterns) >= 3
        assert result.severity == "critical"


# ---------------------------------------------------------------------------
# Age tier amplification
# ---------------------------------------------------------------------------


class TestAgeTierAmplification:
    def test_young_target_amplifies_grooming(self, classifier):
        text = "you're so special to me"
        result_no_tier = classifier.classify(text)
        result_young = classifier.classify(text, target_age_tier="young")
        assert result_young.risk_score > result_no_tier.risk_score

    def test_young_target_amplifies_sexting(self, classifier):
        text = "send me a pic"
        result_no_tier = classifier.classify(text)
        result_young = classifier.classify(text, target_age_tier="young")
        assert result_young.risk_score > result_no_tier.risk_score

    def test_preteen_target_amplifies_grooming(self, classifier):
        text = "you're so special to me"
        result_no_tier = classifier.classify(text)
        result_preteen = classifier.classify(text, target_age_tier="preteen")
        assert result_preteen.risk_score > result_no_tier.risk_score

    def test_young_amplification_is_greater_than_preteen(self, classifier):
        text = "don't tell anyone"
        result_young = classifier.classify(text, target_age_tier="young")
        result_preteen = classifier.classify(text, target_age_tier="preteen")
        assert result_young.risk_score > result_preteen.risk_score

    def test_teen_target_no_amplification(self, classifier):
        text = "you're so special to me"
        result_no_tier = classifier.classify(text)
        result_teen = classifier.classify(text, target_age_tier="teen")
        assert result_teen.risk_score == result_no_tier.risk_score

    def test_bullying_not_amplified_by_age(self, classifier):
        text = "nobody likes you"
        result_no_tier = classifier.classify(text)
        result_young = classifier.classify(text, target_age_tier="young")
        assert result_young.risk_score == result_no_tier.risk_score


# ---------------------------------------------------------------------------
# Conversation history
# ---------------------------------------------------------------------------


class TestConversationHistory:
    def test_history_provides_context(self, classifier):
        """Grooming pattern split across messages should be detected."""
        history = ["you're so special", "don't tell your parents"]
        result = classifier.classify(
            "let's meet up alone", conversation_history=history
        )
        assert result.category == SocialRiskCategory.GROOMING
        assert len(result.matched_patterns) >= 3

    def test_only_last_five_messages_used(self, classifier):
        """Only the last 5 conversation history messages are used."""
        old_msgs = ["our secret"] * 3
        recent_msgs = ["hello", "how are you"] * 3  # 6 msgs total
        history = old_msgs + recent_msgs
        # "our secret" is in early messages, will be dropped since only last 5 used
        result = classifier.classify("hi there", conversation_history=history)
        # The "our secret" messages should be outside the last-5 window
        assert result.category == SocialRiskCategory.NONE

    def test_empty_history(self, classifier):
        result = classifier.classify("hello", conversation_history=[])
        assert result.category == SocialRiskCategory.NONE


# ---------------------------------------------------------------------------
# Severity mapping
# ---------------------------------------------------------------------------


class TestSeverityMapping:
    def test_critical_severity_at_50(self, classifier):
        # Multiple patterns to push score >= 50
        result = classifier.classify(
            "kill yourself, you're ugly, nobody likes you"
        )
        assert result.severity == "critical"
        assert result.risk_score >= 50

    def test_high_severity_at_30(self, classifier):
        result = classifier.classify("I'll hurt you tomorrow")
        assert result.severity == "high"
        assert result.risk_score >= 30

    def test_medium_severity_at_15(self, classifier):
        result = classifier.classify("you're fat")
        assert result.severity == "medium"
        assert result.risk_score >= 15

    def test_low_severity_under_15(self, classifier):
        result = classifier.classify("shut up")
        assert result.severity == "low"
        assert result.risk_score < 15
        assert result.risk_score > 0

    def test_none_severity_no_match(self, classifier):
        result = classifier.classify("hello, how are you today?")
        assert result.severity == "none"
        assert result.risk_score == 0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_string(self, classifier):
        result = classifier.classify("")
        assert result.category == SocialRiskCategory.NONE
        assert result.risk_score == 0

    def test_whitespace_only(self, classifier):
        result = classifier.classify("   \n\t  ")
        assert result.category == SocialRiskCategory.NONE
        assert result.risk_score == 0

    def test_safe_content(self, classifier):
        result = classifier.classify("Let's play Minecraft together!")
        assert result.category == SocialRiskCategory.NONE
        assert result.risk_score == 0

    def test_case_insensitive(self, classifier):
        result = classifier.classify("KILL YOURSELF")
        assert result.category == SocialRiskCategory.CYBERBULLYING
        assert "death_threat" in result.matched_patterns

    def test_risk_score_capped_at_100(self, classifier):
        # Combine many patterns
        text = (
            "kill yourself, you're ugly, nobody likes you, "
            "I'll hurt you, watch your back, go die"
        )
        result = classifier.classify(text)
        assert result.risk_score <= 100

    def test_confidence_capped_at_095(self, classifier):
        text = (
            "kill yourself, you're ugly, nobody likes you, "
            "I'll hurt you, watch your back"
        )
        result = classifier.classify(text)
        assert result.confidence <= 0.95

    def test_confidence_increases_with_score(self, classifier):
        low = classifier.classify("shut up")
        high = classifier.classify("kill yourself, you're ugly, go die")
        assert high.confidence > low.confidence

    def test_details_contains_all_scores(self, classifier):
        result = classifier.classify("you're so special, send me a pic")
        assert "grooming_score" in result.details
        assert "bullying_score" in result.details
        assert "sexting_score" in result.details

    def test_multiple_categories_picks_highest(self, classifier):
        """When grooming and bullying both match, the higher score wins."""
        result = classifier.classify("you're ugly, shut up")
        assert result.category == SocialRiskCategory.CYBERBULLYING
        # Bullying score: 15 (derogatory) + 10 (dismissal) = 25
        assert result.details["bullying_score"] == 25


# ---------------------------------------------------------------------------
# Module-level function
# ---------------------------------------------------------------------------


class TestModuleLevelFunction:
    def test_classify_social_risk_function(self):
        result = classify_social_risk("nobody likes you")
        assert result.category == SocialRiskCategory.CYBERBULLYING
        assert isinstance(result, SocialRiskResult)

    def test_classify_social_risk_with_age_tier(self):
        result = classify_social_risk(
            "you're so special", target_age_tier="young"
        )
        assert result.risk_score > 0

    def test_classify_social_risk_safe_text(self):
        result = classify_social_risk("Good morning! How are you?")
        assert result.category == SocialRiskCategory.NONE
