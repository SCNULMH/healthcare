import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.services.public_data import map_checkup_row_to_risk_payload


class RiskApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_metadata_exposes_submission_roadmap(self):
        response = self.client.get("/risk/metadata")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["product"], "검진AI 리셋코치")
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
        self.assertIn(payload["status"], {"missing_key", "reachable", "network_error", "http_error"})

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
        self.assertEqual(payload["ai_explanation"]["title"], "AI가 이렇게 판단했어요")
        self.assertEqual(len(payload["ai_explanation"]["steps"]), 3)
        self.assertLessEqual(len(payload["plan"]["today_actions"]), 2)

    def test_ocr_extract_accepts_file_upload(self):
        response = self.client.post(
            "/risk/ocr/extract",
            files={"file": ("checkup.pdf", b"sample", "application/pdf")},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "demo_extracted")
        self.assertEqual(payload["prefill"]["lifestyle"]["avg_steps"], 4300)


if __name__ == "__main__":
    unittest.main()
