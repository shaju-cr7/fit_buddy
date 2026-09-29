from django import forms

from .models import UserProfile


class ProfileForm(forms.Form):
    name = forms.CharField(max_length=100)
    age = forms.IntegerField(min_value=16, max_value=100)
    gender = forms.ChoiceField(choices=[("woman", "Woman"), ("man", "Man"), ("nonbinary", "Non-binary"), ("prefer_not_to_say", "Prefer not to say")])
    height_cm = forms.IntegerField(min_value=120, max_value=230)
    weight_kg = forms.DecimalField(min_value=30, max_value=300, decimal_places=1)
    fitness_level = forms.ChoiceField(choices=UserProfile.FITNESS_LEVELS)
    goal = forms.ChoiceField(choices=UserProfile.GOALS)
    activity_level = forms.ChoiceField(choices=[("mostly_sitting", "Mostly sitting"), ("light", "Lightly active"), ("moderate", "Moderately active"), ("very_active", "Very active")])
    workout_days = forms.IntegerField(min_value=1, max_value=7)
    workout_minutes = forms.IntegerField(min_value=15, max_value=180)
    equipment = forms.CharField(max_length=300, required=False)
    dietary_preference = forms.ChoiceField(choices=UserProfile.DIETS)
    food_preferences = forms.CharField(max_length=500, required=False)
    allergies = forms.CharField(max_length=500, required=False)
    water_liters = forms.DecimalField(min_value=0.5, max_value=8, decimal_places=1)
    sleep_hours = forms.DecimalField(min_value=3, max_value=16, decimal_places=1)


class FeedbackForm(forms.Form):
    difficulty = forms.ChoiceField(choices=[("easy", "Easy"), ("right", "Just right"), ("hard", "Hard")])
    rating = forms.IntegerField(min_value=1, max_value=5)
    adherence = forms.IntegerField(min_value=0, max_value=100)
    comments = forms.CharField(max_length=1000, required=False)


class ProgressForm(forms.Form):
    weight_kg = forms.DecimalField(min_value=30, max_value=300, decimal_places=1, required=False)
    activity_minutes = forms.IntegerField(min_value=0, max_value=1440, required=False)
    note = forms.CharField(max_length=300, required=False)