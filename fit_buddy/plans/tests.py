from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from .models import Feedback, Meal, NutritionPlan, UserProfile, WorkoutDay, WorkoutPlan


PLAN = {
    "provider": "local",
    "summary": {"headline": "A steady start", "goal": "General fitness", "weekly_workouts": 1, "session_minutes": 30},
    "weekly_workout_plan": [{"day": "Monday", "focus": "Full body", "duration_minutes": 30, "exercises": [{"name": "Squat", "sets": 2, "repetitions": "8", "rest_seconds": 60, "beginner_alternative": "Chair squat"}], "recovery": "Take a rest day."}],
    "nutrition_guidance": {"daily_calories": 2100, "protein_g": 100, "carbs_g": 220, "fats_g": 70, "hydration_liters": 2},
    "daily_meal_ideas": [{"meal_type": "Breakfast", "name": "Oats", "foods": ["Oats", "Fruit"]}],
    "hydration_and_sleep_tips": ["Sip water through the day."],
    "safety_notes": ["General wellness guidance only."],
    "progress_tracking": {"weekly_check_in": "Check in."},
    "motivation": "Start comfortably.",
}


class FitBuddyAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="member@example.com", email="member@example.com", password="Safe-passphrase-2026")
        self.client.force_login(self.user)

    def profile_data(self):
        return {
            "name": "Alex Member", "age": 30, "gender": "prefer_not_to_say", "height_cm": 170, "weight_kg": 68.5,
            "fitness_level": "beginner", "goal": "general_fitness", "activity_level": "light", "workout_days": 3,
            "workout_minutes": 30, "equipment": "", "dietary_preference": "vegetarian", "food_preferences": "Oats",
            "allergies": "peanuts", "water_liters": 2.0, "sleep_hours": 7.0,
        }

    @patch("plans.views.generate", return_value=PLAN)
    def test_profile_saves_user_data_and_normalized_plan(self, generate):
        response = self.client.post("/api/profile/", self.profile_data(), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(UserProfile.objects.filter(user=self.user, allergies="peanuts").exists())
        self.assertEqual(WorkoutPlan.objects.filter(user=self.user).count(), 1)
        self.assertEqual(WorkoutDay.objects.count(), 1)
        self.assertEqual(NutritionPlan.objects.count(), 1)
        self.assertEqual(Meal.objects.count(), 1)
        self.assertEqual(str(generate.call_args.args[1]["profile"]["weight_kg"]), "68.5")

    def test_profile_requires_authentication_and_valid_values(self):
        self.client.logout()
        response = self.client.post("/api/profile/", {}, content_type="application/json")
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user)
        invalid = self.profile_data()
        invalid["workout_days"] = 9
        response = self.client.post("/api/profile/", invalid, content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_page_sets_csrf_cookie(self):
        response = self.client.get("/profile/")
        self.assertIn("csrftoken", response.cookies)

    def test_plan_cannot_be_read_by_another_user(self):
        profile = UserProfile.objects.create(user=self.user, **{key: value for key, value in self.profile_data().items()})
        plan = WorkoutPlan.objects.create(user=self.user, profile=profile, data=PLAN)
        other = User.objects.create_user(username="other@example.com", password="Other-passphrase-2026")
        self.client.force_login(other)
        response = self.client.get(f"/api/plan/{plan.id}/")
        self.assertEqual(response.status_code, 404)

    def test_feedback_is_saved_and_creates_updated_plan(self):
        profile = UserProfile.objects.create(user=self.user, **self.profile_data())
        WorkoutPlan.objects.create(user=self.user, profile=profile, data=PLAN)
        with patch("plans.views.generate", return_value=PLAN):
            response = self.client.post("/api/feedback/", {"difficulty": "hard", "rating": 3, "adherence": 60, "comments": "Need more recovery."}, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Feedback.objects.count(), 1)
        self.assertEqual(WorkoutPlan.objects.count(), 2)