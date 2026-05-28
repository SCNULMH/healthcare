import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app
from app.services import firebase_backend
from app.services.account_store import create_session_token
from app.services.ocr_runtime import UploadedDocument, _build_prefill_from_fields
from app.services.public_data import map_checkup_row_to_risk_payload


class RiskApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_metadata_exposes_submission_roadmap(self):
        response = self.client.get("/risk/metadata")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["product"], "검진AI 리셋코치")
        self.assertIn("model", payload)
        self.assertIn("status", payload["model"])
        self.assertIn("ocr", payload)
        self.assertIn(payload["ocr"]["provider"], {"demo", "openai", "off", "disabled"})
        self.assertTrue(any("HealthKit" in item for item in payload["roadmap"]))

    def test_readiness_reports_key_state(self):
        response = self.client.get("/health/ready")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertIn("public_data_key_configured", payload)

    def test_account_status_reports_firebase_fallback_safely(self):
        response = self.client.get("/account/status")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("firebase_requested", payload)
        self.assertIn("firebase_enabled", payload)
        self.assertIn("credential_configured", payload)
        if payload["database_backend"] == "firebase" and not payload["credential_configured"]:
            self.assertEqual(payload["fallback_backend"], "sqlite")

    def test_firebase_backend_disables_without_credentials(self):
        fake_settings = SimpleNamespace(
            database_backend="firebase",
            firebase_credentials_path=None,
            firebase_credentials_json=None,
        )

        with patch("app.services.firebase_backend.get_settings", return_value=fake_settings):
            self.assertTrue(firebase_backend.is_requested())
            self.assertFalse(firebase_backend.has_credentials())
            self.assertFalse(firebase_backend.is_enabled())

    def test_public_data_status_is_safe_without_key(self):
        response = self.client.get("/health/public-data")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn(payload["status"], {"missing_key", "reachable", "network_error", "http_error", "demo", "fallback_demo"})

    def test_checkup_row_maps_to_risk_prefill(self):
        row = {
            "연령대코드(5세단위)": "14",
            "성별": "2",
            "신장(5cm단위)": "160",
            "체중(5kg단위)": "75",
            "허리둘레": "89.0",
            "수축기혈압": "127",
            "이완기혈압": "73",
            "식전혈당(공복혈당)": "84",
            "총콜레스테롤": "",
            "HDL콜레스테롤": "",
            "LDL콜레스테롤": "",
            "트리글리세라이드": "",
            "흡연상태": "1",
            "음주여부": "0",
            "기준년도": "2022",
        }

        payload = map_checkup_row_to_risk_payload(row)

        self.assertEqual(payload["health"]["sex"], "female")
        self.assertEqual(payload["health"]["age"], 68)
        self.assertEqual(payload["health"]["fasting_glucose"], 84)
        self.assertEqual(payload["lifestyle"]["smoking"], "never")
        self.assertEqual(payload["lifestyle"]["drinking_per_week"], 0)
        self.assertEqual(payload["source"]["year"], "2022")

    def test_demo_payload_predicts_successfully(self):
        demo = self.client.get("/risk/demo").json()
        response = self.client.post("/risk/predict", json=demo)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("risks", payload)
        self.assertIn("plan", payload)
        self.assertIn("ai_explanation", payload)
        self.assertIn("engine", payload)
        self.assertIn("reliability", payload)
        self.assertEqual(payload["ai_explanation"]["title"], "AI가 이렇게 판단했어요")
        self.assertEqual(len(payload["ai_explanation"]["steps"]), 3)
        self.assertIn("criteria", payload["ai_explanation"])
        self.assertLessEqual(len(payload["plan"]["today_actions"]), 2)
        self.assertIn("impact_summary", payload["plan"])
        self.assertIn("cards", payload["reliability"])

    def test_prediction_accepts_unknown_lipid_values(self):
        demo = self.client.get("/risk/demo").json()
        demo["health"].update(
            {
                "total_cholesterol": None,
                "hdl": None,
                "ldl": None,
                "triglyceride": None,
                "lipid_unknown": True,
            }
        )

        response = self.client.post("/risk/predict", json=demo)
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("지질 수치", " ".join(payload["input_notes"]))
        dyslipidemia = next(item for item in payload["risks"] if item["key"] == "dyslipidemia")
        self.assertTrue(any("직접 수치 판단" in reason for reason in dyslipidemia["reasons"]))

    def test_prediction_accepts_partial_unknown_lipid_values(self):
        demo = self.client.get("/risk/demo").json()
        demo["health"].update({"hdl": None, "unknown_fields": ["hdl"]})

        response = self.client.post("/risk/predict", json=demo)
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("HDL", " ".join(payload["input_notes"]))
        dyslipidemia = next(item for item in payload["risks"] if item["key"] == "dyslipidemia")
        self.assertTrue(any("일부 지질 수치" in reason for reason in dyslipidemia["reasons"]))

    def test_prediction_uses_known_blood_pressure_when_one_field_unknown(self):
        demo = self.client.get("/risk/demo").json()
        demo["health"].update({"systolic_bp": 145, "diastolic_bp": None, "unknown_fields": ["diastolic_bp"]})

        response = self.client.post("/risk/predict", json=demo)
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        hypertension = next(item for item in payload["risks"] if item["key"] == "hypertension")
        self.assertTrue(any("고혈압 위험 기준" in reason for reason in hypertension["reasons"]))

    def test_save_result_requires_login_token(self):
        demo = self.client.get("/risk/demo").json()
        prediction = self.client.post("/risk/predict", json=demo).json()

        response = self.client.post(
            "/risk/save-result",
            json={**demo, "bmi": prediction["bmi"], "risks": prediction["risks"], "plan": prediction["plan"]},
        )

        self.assertEqual(response.status_code, 401)
        self.assertIn("로그인", response.json()["detail"])

    def test_save_result_stores_authenticated_history_and_compares(self):
        user_id = "test-client-history"
        token = create_session_token(user_id)
        demo = self.client.get("/risk/demo").json()
        demo["client_id"] = user_id

        first_prediction = self.client.post("/risk/predict", json=demo).json()
        first = self.client.post(
            "/risk/save-result",
            json={
                **demo,
                "user_id": user_id,
                "session_token": token,
                "bmi": first_prediction["bmi"],
                "risks": first_prediction["risks"],
                "plan": first_prediction["plan"],
            },
        )
        second_payload = self.client.get("/risk/demo").json()
        second_payload["client_id"] = user_id
        second_payload["health"]["fasting_glucose"] = 99
        second_prediction = self.client.post("/risk/predict", json=second_payload).json()
        second = self.client.post(
            "/risk/save-result",
            json={
                **second_payload,
                "user_id": user_id,
                "session_token": token,
                "bmi": second_prediction["bmi"],
                "risks": second_prediction["risks"],
                "plan": second_prediction["plan"],
            },
        )
        history = self.client.get(f"/risk/history/{user_id}")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["comparison"]["status"], "compared")
        self.assertEqual(history.status_code, 200)
        self.assertGreaterEqual(len(history.json()["items"]), 2)

    def test_ocr_extract_accepts_file_upload(self):
        response = self.client.post(
            "/risk/ocr/extract",
            files={"file": ("checkup.pdf", b"sample", "application/pdf")},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "demo_extracted")
        self.assertEqual(payload["provider"], "demo")
        self.assertEqual(payload["prefill"]["lifestyle"]["avg_steps"], 4300)

    def test_ocr_result_maps_korean_labels_to_prefill(self):
        document = UploadedDocument("checkup.png", "image/png", b"sample")
        raw_fields = {
            "health": {
                "성별": "남성",
                "키": "172 cm",
                "체중": "82 kg",
                "식전혈당(공복혈당)": "132 mg/dL",
                "수축기혈압": "133",
                "HDL콜레스테롤": "42",
            },
            "extracted_fields": [],
        }

        payload = _build_prefill_from_fields(document, raw_fields, Settings())

        self.assertEqual(payload["status"], "ocr_extracted")
        self.assertEqual(payload["prefill"]["health"]["sex"], "male")
        self.assertEqual(payload["prefill"]["health"]["height_cm"], 172)
        self.assertEqual(payload["prefill"]["health"]["fasting_glucose"], 132)
        self.assertIn("ldl", payload["prefill"]["health"]["unknown_fields"])
        self.assertIn("공복혈당", payload["extracted_fields"])

    def test_ocr_result_ai_matches_raw_text_lines(self):
        document = UploadedDocument("checkup.txt", "text/plain", b"sample")
        raw_fields = {
            "raw_text": """
            신체계측 신장 172 cm
            몸무게 82 kg
            혈압 132/86 mmHg
            식전혈당(공복혈당) 128 mg/dL
            총 콜레스테롤 218
            HDL-콜레스테롤 42
            LDL 콜레스테롤 138
            트리글리세라이드 185
            """,
            "warnings": [],
        }

        payload = _build_prefill_from_fields(document, raw_fields, Settings())

        self.assertEqual(payload["status"], "ocr_extracted")
        self.assertEqual(payload["prefill"]["health"]["height_cm"], 172)
        self.assertEqual(payload["prefill"]["health"]["systolic_bp"], 132)
        self.assertEqual(payload["prefill"]["health"]["diastolic_bp"], 86)
        self.assertEqual(payload["prefill"]["health"]["fasting_glucose"], 128)
        self.assertEqual(payload["prefill"]["health"]["triglyceride"], 185)
        self.assertEqual(payload["prefill"]["health"]["unknown_fields"], [])
        self.assertIn("match_details", payload)

    def test_ocr_result_ai_matches_table_rows(self):
        document = UploadedDocument("checkup.png", "image/png", b"sample")
        raw_fields = {
            "rows": [
                {"검사항목": "최고 혈압", "결과": "134"},
                {"검사항목": "최저 혈압", "결과": "88"},
                {"검사항목": "고밀도 콜레스테롤", "결과": "47"},
                {"검사항목": "저밀도 콜레스테롤", "결과": "141"},
            ]
        }

        payload = _build_prefill_from_fields(document, raw_fields, Settings())

        self.assertEqual(payload["prefill"]["health"]["systolic_bp"], 134)
        self.assertEqual(payload["prefill"]["health"]["diastolic_bp"], 88)
        self.assertEqual(payload["prefill"]["health"]["hdl"], 47)
        self.assertEqual(payload["prefill"]["health"]["ldl"], 141)
        self.assertIn("fasting_glucose", payload["prefill"]["health"]["unknown_fields"])


if __name__ == "__main__":
    unittest.main()
