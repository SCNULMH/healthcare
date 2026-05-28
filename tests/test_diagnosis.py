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


def risk_by_key(risks, key):
    return next(item for item in risks if item.key == key)


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

    def test_all_lipid_unknown_uses_lifestyle_fallback(self):
        risks = evaluate_health_risks(
            health(
                total_cholesterol=None,
                hdl=None,
                ldl=None,
                triglyceride=None,
                unknown_fields=["total_cholesterol", "hdl", "ldl", "triglyceride"],
                lipid_unknown=True,
            ),
            lifestyle(eating_out_per_week=6, late_meals_per_week=4, exercise_per_week=0, avg_steps=3200),
        )
        dyslipidemia = risk_by_key(risks, "dyslipidemia")
        reasons = " ".join(dyslipidemia.reasons)

        self.assertIn("직접 수치 판단은 제외", reasons)
        self.assertIn("외식", reasons)
        self.assertIn("야식", reasons)
        self.assertGreaterEqual(dyslipidemia.probability, 35)

    def test_partial_lipid_unknown_uses_known_lipid_values_only(self):
        risks = evaluate_health_risks(
            health(
                hdl=None,
                unknown_fields=["hdl"],
                total_cholesterol=241,
                ldl=120,
                triglyceride=130,
                lipid_unknown=False,
            ),
            lifestyle(eating_out_per_week=1, late_meals_per_week=0, exercise_per_week=3, avg_steps=7500),
        )
        dyslipidemia = risk_by_key(risks, "dyslipidemia")
        reasons = " ".join(dyslipidemia.reasons)

        self.assertIn("일부 지질 수치", reasons)
        self.assertIn("위험 범위", reasons)

    def test_single_unknown_blood_pressure_still_uses_known_high_value(self):
        risks = evaluate_health_risks(
            health(
                systolic_bp=145,
                diastolic_bp=None,
                unknown_fields=["diastolic_bp"],
                bp_unknown=False,
            ),
            lifestyle(eating_out_per_week=1, drinking_per_week=0, drinking_per_month=0, drinks_per_session=0),
        )
        hypertension = risk_by_key(risks, "hypertension")

        self.assertIn("고혈압 위험 기준", " ".join(hypertension.reasons))
        self.assertGreaterEqual(hypertension.probability, 59)

    def test_drinking_level_boundaries(self):
        self.assertEqual(lifestyle(drinking_per_week=0, drinking_per_month=0, drinks_per_session=0).drinking_level, "none")
        self.assertEqual(lifestyle(drinking_per_week=0, drinking_per_month=3, drinks_per_session=2).drinking_level, "light")
        self.assertEqual(lifestyle(drinking_per_week=1, drinking_per_month=4, drinks_per_session=4).drinking_level, "moderate")
        self.assertEqual(lifestyle(drinking_per_week=2, drinking_per_month=1, drinks_per_session=5).drinking_level, "heavy")

    def test_heavy_drinking_increases_hypertension_more_than_light(self):
        base_health = health(systolic_bp=None, diastolic_bp=None, bp_unknown=True)
        light = risk_by_key(
            evaluate_health_risks(base_health, lifestyle(drinking_per_week=0, drinking_per_month=2, drinks_per_session=1)),
            "hypertension",
        )
        heavy = risk_by_key(
            evaluate_health_risks(base_health, lifestyle(drinking_per_week=3, drinking_per_month=0, drinks_per_session=5)),
            "hypertension",
        )

        self.assertGreater(heavy.probability, light.probability)
        self.assertIn("음주", " ".join(heavy.reasons))


if __name__ == "__main__":
    unittest.main()
