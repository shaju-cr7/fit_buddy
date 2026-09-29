from django.contrib import admin

from .models import Feedback, Meal, NutritionPlan, Progress, Tip, UserProfile, WorkoutDay, WorkoutPlan


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "goal", "fitness_level", "updated_at")
    search_fields = ("name", "user__email", "user__username")
    list_filter = ("goal", "fitness_level", "dietary_preference")


@admin.register(WorkoutPlan)
class WorkoutPlanAdmin(admin.ModelAdmin):
    list_display = ("user", "source", "created_at")
    list_filter = ("source", "created_at")


admin.site.register((WorkoutDay, NutritionPlan, Meal, Feedback, Progress, Tip))