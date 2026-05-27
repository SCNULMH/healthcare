import unittest

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app
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
        self.assertEqual(payload["lifestyle"]["drinking"], "none")
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

    def test_predict_stores_anonymous_history_and_compares(self):
        demo = self.client.get("/risk/demo").json()
        demo["client_id"] = "test-client-history"

        first = self.client.post("/risk/predict", json=demo)
        second_payload = self.client.get("/risk/demo").json()
        second_payload["client_id"] = "test-client-history"
        second_payload["health"]["fasting_glucose"] = 99
        second = self.client.post("/risk/predict", json=second_payload)
        history = self.client.get("/risk/history/test-client-history")

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


if __name__ == "__main__":
    unittest.main()
