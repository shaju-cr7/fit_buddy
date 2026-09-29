import asyncio
import hmac
import json
import os
import time
from collections import defaultdict, deque
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.responses import JSONResponse

load_dotenv()

app = FastAPI(title="FitBuddy AI Service", version="1.0.0")
_requests: dict[str, deque[float]] = defaultdict(deque)
RATE_LIMIT = 30
RATE_WINDOW_SECONDS = 3600


class GenerationRequest(BaseModel):
    profile: dict[str, Any]
    existing_plan: dict[str, Any] | None = None
    feedback: dict[str, Any] | None = None


@app.middleware("http")
async def limit_generation_requests(request: Request, call_next):
    if request.url.path.startswith("/api/generate/"):
        expected_token = os.getenv("AI_SERVICE_TOKEN", "local-only-fitbuddy-service-token-change-before-deployment")
        supplied_token = request.headers.get("X-FitBuddy-Service-Token", "")
        if not hmac.compare_digest(supplied_token, expected_token):
            return JSONResponse(status_code=401, content={"detail": "Trusted service authentication required."})
        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        recent = _requests[key]
        while recent and now - recent[0] > RATE_WINDOW_SECONDS:
            recent.popleft()
        if len(recent) >= RATE_LIMIT:
            return JSONResponse(status_code=429, content={"detail": "Too many generation requests. Try again later."})
        recent.append(now)
    return await call_next(request)


@app.get("/health/")
def health():
    return {"status": "ok", "provider": "gemini" if os.getenv("GEMINI_API_KEY") else "local"}


def fallback_plan(profile: dict[str, Any]) -> dict[str, Any]:
    days = max(1, min(5, int(profile.get("workout_days", 3))))
    level = profile.get("fitness_level", "beginner")
    duration = max(15, min(90, int(profile.get("workout_minutes", 40))))
    equipment = str(profile.get("equipment", "bodyweight"))
    movements = [
        ("Squat to chair", "3", "8-10", "Bodyweight squat to a comfortable depth"),
        ("Incline push-up", "3", "6-10", "Wall push-up"),
        ("Hip hinge", "3", "8-12", "Glute bridge"),
        ("Supported row", "3", "8-12", "Prone W raise"),
        ("Dead bug", "2", "6 each side", "Heel taps"),
    ]
    if level == "advanced":
        movements = [(name, "4", reps, alt) for name, _, reps, alt in movements]
    weekly = []
    for index in range(days):
        day = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"][index]
        focus = ["Full body strength", "Low-impact cardio + mobility", "Full body strength", "Cardio + core", "Full body strength"][index]
        exercises = []
        for name, sets, reps, alternative in movements:
            if name == "Supported row" and not equipment.strip():
                name = "Prone W raise"
            exercises.append({
                "name": name,
                "sets": sets,
                "repetitions": reps,
                "duration_minutes": None,
                "rest_seconds": 60 if level == "beginner" else 45,
                "beginner_alternative": alternative,
            })
        weekly.append({"day": day, "focus": focus, "duration_minutes": duration, "exercises": exercises, "recovery": "Keep at least one easy or rest day between strength sessions."})

    weight = float(profile.get("weight_kg", 70))
    height = float(profile.get("height_cm", 170))
    age = int(profile.get("age", 30))
    gender = profile.get("gender", "prefer_not_to_say")
    gender_adjustment = -161 if gender == "woman" else (5 if gender == "man" else -78)
    activity_multiplier = {"mostly_sitting": 1.2, "light": 1.375, "moderate": 1.55, "very_active": 1.7}.get(profile.get("activity_level"), 1.375)
    estimated_energy = (10 * weight + 6.25 * height - 5 * age + gender_adjustment) * activity_multiplier
    goal = profile.get("goal")
    estimated_energy *= 0.92 if goal == "weight_loss" else (1.05 if goal == "muscle_gain" else 1)
    calories = round(estimated_energy / 50) * 50
    protein = round(min(weight * 1.6, 180))
    fat = round(calories * 0.28 / 9)
    carbs = round(max(0, calories - protein * 4 - fat * 9) / 4)
    diet = profile.get("dietary_preference", "vegetarian")
    if diet == "vegan":
        protein_foods = "beans, lentils, tofu, tempeh and fortified soy foods"
    elif diet == "vegetarian":
        protein_foods = "Greek yogurt, eggs, beans, lentils, tofu and cottage cheese"
    else:
        protein_foods = "fish, poultry, eggs, dairy, beans and lentils"
    allergy_note = profile.get("allergies") or "No allergies listed; check labels and avoid any food that causes a reaction."

    return {
        "provider": "local",
        "summary": {
            "headline": "A steady plan built around your week",
            "goal": goal.replace("_", " ").title() if goal else "General fitness",
            "fitness_level": level.title(),
            "weekly_workouts": days,
            "session_minutes": duration,
        },
        "weekly_workout_plan": weekly,
        "nutrition_guidance": {
            "daily_calories": calories,
            "protein_g": protein,
            "carbs_g": carbs,
            "fats_g": fat,
            "dietary_preference": diet,
            "hydration_liters": float(profile.get("water_liters", 2.0)),
            "notes": "Energy and macro figures are broad estimates, not a prescription. Adjust based on comfort and progress with a qualified professional.",
        },
        "daily_meal_ideas": [
            {"meal_type": "Breakfast", "name": "Oats with fruit and protein", "foods": ["Oats", "Seasonal fruit", protein_foods], "notes": "Choose portions that feel satisfying; check ingredients against your allergies."},
            {"meal_type": "Lunch", "name": "Balanced grain bowl", "foods": ["Brown rice or whole grains", protein_foods, "Mixed vegetables"], "notes": "Use an allergy-safe dressing and add a source of healthy fats."},
            {"meal_type": "Dinner", "name": "Colorful plate", "foods": [protein_foods, "Roasted or steamed vegetables", "Potato or whole grains"], "notes": "Keep meals flexible around your preferences."},
            {"meal_type": "Snack", "name": "Simple snack", "foods": ["Fruit", "A protein-rich, allergy-safe option"], "notes": "A snack is optional; follow hunger and your schedule."},
        ],
        "hydration_and_sleep_tips": [
            f"Keep water nearby and sip through the day; your current intake is {profile.get('water_liters', 2)} L.",
            f"Aim for a consistent sleep routine; your current average is {profile.get('sleep_hours', 7)} hours.",
        ],
        "safety_notes": [
            "Stop exercise if you feel sharp pain, dizziness or unusual shortness of breath.",
            f"Food allergy note: {allergy_note}",
            "This is general wellness guidance, not medical care. Ask a qualified healthcare professional before major changes, especially with a health condition or injury.",
        ],
        "progress_tracking": {"weekly_check_in": "Record workouts completed, energy, sleep and how the plan felt.", "focus": "Look for gradual, sustainable changes over several weeks."},
        "motivation": "Consistency grows from small sessions you can repeat. Start at a comfortable pace and build gradually.",
    }


def fallback_tips(profile: dict[str, Any]) -> dict[str, Any]:
    return {"tips": [
        {"category": "fitness", "content": "Start each session with five easy minutes and leave a few comfortable reps in reserve."},
        {"category": "nutrition", "content": "Include a satisfying protein source and colorful produce in meals when practical."},
        {"category": "hydration", "content": "Drink regularly across the day and around activity; needs vary with weather and exercise."},
        {"category": "sleep", "content": "A consistent wind-down and wake time can make sleep easier to protect."},
        {"category": "motivation", "content": f"Your {profile.get('workout_days', 3)} planned workout days are a useful starting point. Showing up counts."},
    ]}


def generate_with_gemini(prompt: str) -> dict[str, Any]:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            system_instruction=(
                "You are FitBuddy, a cautious general-wellness assistant. Use only supplied profile data. "
                "Never diagnose, prescribe medication, recommend starvation or unsafe exercise, or ignore allergies. "
                "Keep recommendations practical, gradual, and age-appropriate. If risk is unclear, advise professional help. "
                "Return only valid JSON matching the requested sections."
            ),
            temperature=0.4,
        ),
    )
    text = response.text or "{}"
    return json.loads(text)


def create_plan(request: GenerationRequest) -> dict[str, Any]:
    if not os.getenv("GEMINI_API_KEY"):
        return fallback_plan(request.profile)
    prompt = """Create a personalized fitness and nutrition plan. Use the supplied profile only.
Return JSON with: summary (object), weekly_workout_plan (array of day/focus/duration_minutes/exercises/recovery),
nutrition_guidance (object with daily_calories, protein_g, carbs_g, fats_g, dietary_preference, hydration_liters, notes),
daily_meal_ideas (array of meal_type/name/foods/notes), hydration_and_sleep_tips (array), safety_notes (array),
progress_tracking (object), motivation (string). Each exercise has name, sets, repetitions, duration_minutes, rest_seconds,
beginner_alternative. Make all food allergy-safe. Calorie and macro values are estimates, not medical prescriptions.
Use gradual, realistic training and rest days. Profile JSON: """ + json.dumps(request.profile)
    return generate_with_gemini(prompt)


def validate_plan_shape(result: dict[str, Any]) -> dict[str, Any]:
    required = {
        "summary": dict,
        "weekly_workout_plan": list,
        "nutrition_guidance": dict,
        "daily_meal_ideas": list,
        "hydration_and_sleep_tips": list,
        "safety_notes": list,
        "progress_tracking": dict,
        "motivation": str,
    }
    if not isinstance(result, dict) or any(not isinstance(result.get(key), kind) for key, kind in required.items()):
        raise HTTPException(status_code=502, detail="The AI response was missing valid plan sections.")
    if any(not isinstance(day, dict) or not isinstance(day.get("exercises", []), list) for day in result["weekly_workout_plan"]):
        raise HTTPException(status_code=502, detail="The AI response contained an invalid workout schedule.")
    if any(not isinstance(meal, dict) or not isinstance(meal.get("foods", []), list) for meal in result["daily_meal_ideas"]):
        raise HTTPException(status_code=502, detail="The AI response contained invalid meal ideas.")
    if any(not isinstance(note, str) for note in result["safety_notes"] + result["hydration_and_sleep_tips"]):
        raise HTTPException(status_code=502, detail="The AI response contained invalid wellness notes.")
    return result


@app.post("/api/generate/plan/")
async def generate_plan(request: GenerationRequest):
    try:
        result = await asyncio.to_thread(create_plan, request)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Gemini plan generation failed. Check the AI service logs and API configuration.") from exc
    return validate_plan_shape(result)


@app.post("/api/generate/workout/")
async def generate_workout(request: GenerationRequest):
    return {"weekly_workout_plan": (await generate_plan(request))["weekly_workout_plan"]}


@app.post("/api/generate/nutrition/")
async def generate_nutrition(request: GenerationRequest):
    result = await generate_plan(request)
    return {"nutrition_guidance": result["nutrition_guidance"], "daily_meal_ideas": result["daily_meal_ideas"], "hydration_and_sleep_tips": result["hydration_and_sleep_tips"], "safety_notes": result["safety_notes"]}


@app.post("/api/generate/feedback-update/")
async def update_from_feedback(request: GenerationRequest):
    if not request.existing_plan or not request.feedback:
        raise HTTPException(status_code=400, detail="Existing plan and feedback are required.")
    if not os.getenv("GEMINI_API_KEY"):
        result = fallback_plan(request.profile)
        difficulty = request.feedback.get("difficulty")
        if difficulty == "hard":
            result["summary"]["headline"] = "A gentler plan based on your check-in"
            adjusted_minutes = max(15, int(result["summary"]["session_minutes"] * 0.8))
            result["summary"]["session_minutes"] = adjusted_minutes
            for day in result["weekly_workout_plan"]:
                day["duration_minutes"] = adjusted_minutes
        elif difficulty == "easy":
            result["summary"]["headline"] = "A small step forward from your check-in"
        result["provider"] = "local"
        return result
    prompt = """Update this wellness plan in response to the user's feedback. Preserve allergy and safety constraints.
Return the same eight-section JSON structure as the original plan. Make small, appropriate adjustments; do not suggest
training through pain or extreme dietary changes. PROFILE: """ + json.dumps(request.profile) + " FEEDBACK: " + json.dumps(request.feedback) + " CURRENT PLAN: " + json.dumps(request.existing_plan)
    try:
        result = await asyncio.to_thread(generate_with_gemini, prompt)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Gemini could not update the plan. Please try again.") from exc
    return validate_plan_shape(result)


@app.post("/api/generate/tips/")
async def generate_tips(request: GenerationRequest):
    if not os.getenv("GEMINI_API_KEY"):
        return fallback_tips(request.profile)
    prompt = "Return JSON with a tips array of 5 concise objects {category, content}. Categories: fitness, nutrition, hydration, sleep, motivation. Keep suggestions safe and personalized to this profile: " + json.dumps(request.profile)
    try:
        result = await asyncio.to_thread(generate_with_gemini, prompt)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Gemini could not generate tips. Please try again.") from exc
    return result