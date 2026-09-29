import httpx
from django.conf import settings
import json


class AIServiceError(Exception):
    pass


def generate(path, payload):
    try:
        json_payload = json.loads(json.dumps(payload, default=float))
        response = httpx.post(
            f"{settings.AI_SERVICE_URL}{path}",
            json=json_payload,
            headers={"X-FitBuddy-Service-Token": settings.AI_SERVICE_TOKEN},
            timeout=45,
        )
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise AIServiceError("The AI service is unavailable. Check that FastAPI is running, then try again.") from exc


def persist_plan(user, profile, data):
    from .models import Meal, NutritionPlan, WorkoutDay, WorkoutPlan

    plan = WorkoutPlan.objects.create(user=user, profile=profile, data=data, source=data.get("provider", "gemini"))
    for day in data.get("weekly_workout_plan", []):
        WorkoutDay.objects.create(
            workout_plan=plan,
            day=str(day.get("day", "Workout"))[:30],
            focus=str(day.get("focus", ""))[:100],
            exercises=day.get("exercises", []),
            recovery=str(day.get("recovery", ""))[:300],
        )
    nutrition_data = data.get("nutrition_guidance", {})
    nutrition = NutritionPlan.objects.create(workout_plan=plan, data=nutrition_data)
    for meal in data.get("daily_meal_ideas", []):
        Meal.objects.create(
            nutrition_plan=nutrition,
            category=str(meal.get("meal_type", "meal"))[:30],
            name=str(meal.get("name", "Meal idea"))[:160],
            foods=meal.get("foods", []),
            notes=str(meal.get("notes", ""))[:300],
        )
    return plan