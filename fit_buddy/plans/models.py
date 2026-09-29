from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    FITNESS_LEVELS = [(value, value.title()) for value in ("beginner", "intermediate", "advanced")]
    GOALS = [(value, label) for value, label in (
        ("weight_loss", "Weight loss"),
        ("muscle_gain", "Muscle gain"),
        ("maintenance", "Weight maintenance"),
        ("general_fitness", "General fitness"),
    )]
    DIETS = [(value, value.title().replace("_", "-")) for value in ("vegetarian", "non_vegetarian", "vegan")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="fit_profile")
    name = models.CharField(max_length=100)
    age = models.PositiveSmallIntegerField()
    gender = models.CharField(max_length=30)
    height_cm = models.PositiveSmallIntegerField()
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1)
    fitness_level = models.CharField(max_length=20, choices=FITNESS_LEVELS)
    goal = models.CharField(max_length=30, choices=GOALS)
    activity_level = models.CharField(max_length=30)
    workout_days = models.PositiveSmallIntegerField()
    workout_minutes = models.PositiveSmallIntegerField()
    equipment = models.CharField(max_length=300, blank=True)
    dietary_preference = models.CharField(max_length=24, choices=DIETS)
    food_preferences = models.CharField(max_length=500, blank=True)
    allergies = models.CharField(max_length=500, blank=True)
    water_liters = models.DecimalField(max_digits=3, decimal_places=1)
    sleep_hours = models.DecimalField(max_digits=3, decimal_places=1)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.user})"


class WorkoutPlan(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="workout_plans")
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="plans")
    data = models.JSONField(default=dict)
    source = models.CharField(max_length=20, default="gemini")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Plan for {self.user} · {self.created_at:%Y-%m-%d}"


class WorkoutDay(models.Model):
    workout_plan = models.ForeignKey(WorkoutPlan, on_delete=models.CASCADE, related_name="days")
    day = models.CharField(max_length=30)
    focus = models.CharField(max_length=100, blank=True)
    exercises = models.JSONField(default=list)
    recovery = models.CharField(max_length=300, blank=True)


class NutritionPlan(models.Model):
    workout_plan = models.OneToOneField(WorkoutPlan, on_delete=models.CASCADE, related_name="nutrition")
    data = models.JSONField(default=dict)


class Meal(models.Model):
    nutrition_plan = models.ForeignKey(NutritionPlan, on_delete=models.CASCADE, related_name="meals")
    category = models.CharField(max_length=30)
    name = models.CharField(max_length=160)
    foods = models.JSONField(default=list)
    notes = models.CharField(max_length=300, blank=True)


class Feedback(models.Model):
    DIFFICULTIES = [(value, value.title()) for value in ("easy", "right", "hard")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="feedback_entries")
    workout_plan = models.ForeignKey(WorkoutPlan, on_delete=models.CASCADE, related_name="feedback_entries")
    difficulty = models.CharField(max_length=12, choices=DIFFICULTIES)
    rating = models.PositiveSmallIntegerField()
    adherence = models.PositiveSmallIntegerField()
    comments = models.TextField(blank=True, max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Progress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="progress_entries")
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    activity_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    note = models.CharField(max_length=300, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at"]


class Tip(models.Model):
    CATEGORIES = [(value, value.title()) for value in ("fitness", "nutrition", "hydration", "sleep", "motivation")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tips")
    category = models.CharField(max_length=20, choices=CATEGORIES)
    content = models.CharField(max_length=500)
    created_at = models.DateField(auto_now_add=True)