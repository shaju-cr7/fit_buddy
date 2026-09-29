import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from .main import app


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, headers={"X-FitBuddy-Service-Token": "local-only-fitbuddy-service-token-change-before-deployment"})
        self.payload = {"profile": {
            "name": "Sam", "age": 29, "gender": "prefer_not_to_say", "height_cm": 170, "weight_kg": 65,
            "fitness_level": "beginner", "goal": "general_fitness", "activity_level": "light", "workout_days": 3,
            "workout_minutes": 30, "equipment": "", "dietary_preference": "vegan", "food_preferences": "Lentils",
            "allergies": "peanuts", "water_liters": 2, "sleep_hours": 7,
        }}

    @patch.dict("os.environ", {}, clear=True)
    def test_local_plan_returns_required_safe_sections(self):
        response = self.client.post("/api/generate/plan/", json=self.payload)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["provider"], "local")
        self.assertEqual(len(result["weekly_workout_plan"]), 3)
        self.assertEqual(result["nutrition_guidance"]["dietary_preference"], "vegan")
        self.assertEqual(len(result["safety_notes"]), 3)
        self.assertIn("tofu", result["daily_meal_ideas"][0]["foods"][2])
        self.assertNotIn("peanut", " ".join(result["daily_meal_ideas"][0]["foods"]).lower())

    @patch.dict("os.environ", {}, clear=True)
    def test_feedback_update_eases_hard_plan(self):
        payload = {**self.payload, "existing_plan": {"summary": {}}, "feedback": {"difficulty": "hard"}}
        response = self.client.post("/api/generate/feedback-update/", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["summary"]["headline"], "A gentler plan based on your check-in")
        self.assertEqual(response.json()["summary"]["session_minutes"], 24)
        self.assertTrue(all(day["duration_minutes"] == 24 for day in response.json()["weekly_workout_plan"]))

    def test_generation_rejects_missing_service_token(self):
        response = TestClient(app).post("/api/generate/plan/", json=self.payload)
        self.assertEqual(response.status_code, 401)

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}, clear=True)
    @patch("fastapi_service.main.generate_with_gemini", return_value={"summary": {}})
    def test_malformed_gemini_plan_returns_controlled_error(self, generate):
        response = self.client.post("/api/generate/plan/", json=self.payload)
        self.assertEqual(response.status_code, 502)
        self.assertIn("valid plan sections", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()