import unittest

from app.services.diagnosis import (
    HealthProfile,
    LifestyleProfile,
    create_personal_plan,
    evaluate_health_risks,
)


def lifestyle(**overrides):
    base = {
        "breakfast_per_week": 3,
        "sugary_drinks_per_week": 7,
        "late_meals_per_week": 3,
        "exercise_per_week": 0,
        "eating_out_per_week": 5,
        "sleep_hours": 6,
        "avg_steps": 4300,
        "smoking": "never",
        "drinking_per_week": 2,
        "drinking_per_month": 0,
        "drinks_per_session": 3,
        "available_minutes_per_day": 15,
    }
    base.update(overrides)
    return LifestyleProfile(**base)


def health(**overrides):
    base = {
        "age": 45,
        "sex": "male",
        "height_cm": 172,
        "weight_kg": 82,
        "waist_cm": 93,
        "systolic_bp": 132,
        "diastolic_bp": 86,
        "fasting_glucose": 132,
        "total_cholesterol": 218,
        "hdl": 42,
        "ldl": 138,
        "triglyceride": 185,
    }
    base.update(overrides)
    return HealthProfile(**base)


class DiagnosisTests(unittest.TestCase):
    def test_diabetes_threshold_uses_fasting_glucose(self):
        low = evaluate_health_risks(health(fasting_glucose=125), lifestyle())[0]
        high = evaluate_health_risks(health(fasting_glucose=126), lifestyle())[0]

        self.assertLess(low.probability, high.probability)
        self.assertIn("공복혈당", " ".join(high.reasons))

    def test_plan_limits_today_actions_to_two_small_actions(self):
        risks = evaluate_health_risks(health(), lifestyle())
        plan = create_personal_plan(health(), lifestyle(), risks)

        self.assertLessEqual(len(plan["today_actions"]), 2)
        self.assertGreater(len(plan["impact_summary"]), 0)
        rendered = " ".join(action["detail"] for action in plan["today_actions"])
        self.assertNotIn("러닝", rendered)
        self.assertNotIn("단백질 쉐이크만", rendered)

    def test_low_exercise_user_gets_low_intensity_action(self):
        risks = evaluate_health_risks(health(), lifestyle(exercise_per_week=0))
        plan = create_personal_plan(health(), lifestyle(exercise_per_week=0), risks)
        rendered = " ".join(action["detail"] for action in plan["today_actions"])

        self.assertTrue("10분" in rendered or "계단 1층" in rendered)


if __name__ == "__main__":
    unittest.main()
