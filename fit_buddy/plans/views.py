import json
from functools import wraps

from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import FeedbackForm, ProgressForm, ProfileForm
from .models import Feedback, Progress, Tip, UserProfile, WorkoutPlan
from .services import AIServiceError, generate, persist_plan


@ensure_csrf_cookie
def page(request, template):
    return render(request, template, {"page_name": template.removesuffix(".html")})


@ensure_csrf_cookie
def admin_page(request):
    if not request.user.is_staff:
        return render(request, "admin.html", status=403)
    return render(request, "admin.html", {"page_name": "admin"})


def read_json(request):
    try:
        return json.loads(request.body or "{}"), None
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, JsonResponse({"error": "Request body must be valid JSON."}, status=400)


def api_auth_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Please sign in to continue."}, status=401)
        return view(request, *args, **kwargs)
    return wrapped


@require_POST
def register(request):
    data, error = read_json(request)
    if error:
        return error
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    if not email or "@" not in email or len(email) > 254:
        return JsonResponse({"error": "Enter a valid email address."}, status=400)
    if len(password) < 8:
        return JsonResponse({"error": "Use a password with at least 8 characters."}, status=400)
    try:
        validate_password(password, User(username=email, email=email))
    except ValidationError as exc:
        return JsonResponse({"error": " ".join(exc.messages)}, status=400)
    if User.objects.filter(username=email).exists():
        return JsonResponse({"error": "An account with this email already exists."}, status=409)
    user = User.objects.create_user(username=email, email=email, password=password)
    auth_login(request, user)
    return JsonResponse({"user": {"email": user.email, "name": user.get_full_name()}} , status=201)


@require_POST
def login(request):
    data, error = read_json(request)
    if error:
        return error
    email = str(data.get("email", "")).strip().lower()
    user = authenticate(request, username=email, password=str(data.get("password", "")))
    if user is None:
        return JsonResponse({"error": "Email or password is incorrect."}, status=400)
    auth_login(request, user)
    return JsonResponse({"user": {"email": user.email, "name": user.get_full_name()}})


@require_POST
@api_auth_required
def logout(request):
    auth_logout(request)
    return JsonResponse({"ok": True})


@require_GET
def me(request):
    if not request.user.is_authenticated:
        return JsonResponse({"authenticated": False})
    profile = getattr(request.user, "fit_profile", None)
    return JsonResponse({
        "authenticated": True,
        "email": request.user.email,
        "name": profile.name if profile else request.user.get_full_name(),
        "is_staff": request.user.is_staff,
        "has_profile": profile is not None,
    })


@require_POST
@api_auth_required
def profile(request):
    data, error = read_json(request)
    if error:
        return error
    form = ProfileForm(data)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data(), "error": "Check the highlighted profile fields."}, status=400)
    profile_obj, _ = UserProfile.objects.update_or_create(user=request.user, defaults=form.cleaned_data)
    try:
        result = generate("/api/generate/plan/", {"profile": form.cleaned_data})
    except AIServiceError as exc:
        return JsonResponse({"error": str(exc), "profile_saved": True}, status=503)
    plan = persist_plan(request.user, profile_obj, result)
    return JsonResponse({"plan_id": plan.id, "plan": result}, status=201)


def plan_payload(plan):
    return {"id": plan.id, "created_at": plan.created_at, **plan.data}


@require_GET
@api_auth_required
def latest_plan(request):
    plan = WorkoutPlan.objects.filter(user=request.user).first()
    if not plan:
        return JsonResponse({"error": "No plan yet. Create your profile to get started."}, status=404)
    return JsonResponse(plan_payload(plan))


@require_GET
@api_auth_required
def get_plan(request, plan_id):
    plan = WorkoutPlan.objects.filter(user=request.user, id=plan_id).first()
    if not plan:
        return JsonResponse({"error": "Plan not found."}, status=404)
    return JsonResponse(plan_payload(plan))


@require_POST
@api_auth_required
def feedback(request):
    data, error = read_json(request)
    if error:
        return error
    form = FeedbackForm(data)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data(), "error": "Check the feedback fields."}, status=400)
    previous = WorkoutPlan.objects.filter(user=request.user).first()
    if not previous:
        return JsonResponse({"error": "Create a plan before sending feedback."}, status=404)
    entry = Feedback.objects.create(user=request.user, workout_plan=previous, **form.cleaned_data)
    profile_obj = previous.profile
    try:
        result = generate("/api/generate/feedback-update/", {
            "profile": {field: getattr(profile_obj, field) for field in ProfileForm.base_fields},
            "existing_plan": previous.data,
            "feedback": form.cleaned_data,
        })
    except AIServiceError as exc:
        return JsonResponse({"error": str(exc), "feedback_saved": True, "feedback_id": entry.id}, status=503)
    plan = persist_plan(request.user, profile_obj, result)
    return JsonResponse({"feedback_id": entry.id, "plan_id": plan.id, "plan": result}, status=201)


@require_http_methods(["GET", "POST"])
@api_auth_required
def progress(request):
    if request.method == "POST":
        data, error = read_json(request)
        if error:
            return error
        form = ProgressForm(data)
        if not form.is_valid():
            return JsonResponse({"errors": form.errors.get_json_data(), "error": "Check the progress values."}, status=400)
        entry = Progress.objects.create(user=request.user, **form.cleaned_data)
        return JsonResponse({"ok": True, "recorded_at": entry.recorded_at}, status=201)
    records = list(Progress.objects.filter(user=request.user).values("weight_kg", "activity_minutes", "note", "recorded_at")[:30])
    feedback_items = list(Feedback.objects.filter(user=request.user).values("difficulty", "rating", "adherence", "comments", "created_at")[:5])
    return JsonResponse({"entries": records, "feedback": feedback_items})


@require_GET
@api_auth_required
def tips(request):
    profile_obj = getattr(request.user, "fit_profile", None)
    if not profile_obj:
        return JsonResponse({"error": "Add your profile to get personalized tips."}, status=404)
    todays_tips = list(Tip.objects.filter(user=request.user, created_at=timezone.localdate()).values("category", "content"))
    if not todays_tips:
        try:
            result = generate("/api/generate/tips/", {"profile": {field: getattr(profile_obj, field) for field in ProfileForm.base_fields}})
        except AIServiceError as exc:
            return JsonResponse({"error": str(exc)}, status=503)
        for item in result.get("tips", []):
            category = item.get("category", "fitness")
            if category not in dict(Tip.CATEGORIES):
                continue
            Tip.objects.create(user=request.user, category=category, content=str(item.get("content", ""))[:500])
        todays_tips = list(Tip.objects.filter(user=request.user, created_at=timezone.localdate()).values("category", "content"))
    return JsonResponse({"tips": todays_tips})

@require_GET
def admin_stats(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "Administrator access required."}, status=403)
    from django.contrib.auth.models import User

    return JsonResponse({
        "users": User.objects.count(),
        "plans": WorkoutPlan.objects.count(),
        "feedback": Feedback.objects.count(),
        "tips": Tip.objects.count(),
        "recent_feedback": list(Feedback.objects.select_related("user").values("user__username", "rating", "difficulty", "created_at")[:8]),
    })