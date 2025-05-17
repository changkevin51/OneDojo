from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import *
from .forms import *
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import views as auth_views
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from portal.models import CustomUser
from admin_adminlte.forms import LoginForm, RegistrationForm, UserPasswordResetForm, UserSetPasswordForm, UserPasswordChangeForm
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Prefetch
from datetime import datetime
from django.http import JsonResponse
import json
from django.utils.timezone import localtime
from django.core.cache import cache
import logging
from datetime import timedelta
logger = logging.getLogger(__name__)

# This register function is not used right now
def register(request):
    """register new user"""
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('register')
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('register')
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect('register')
        user = CustomUser.objects.create_user(username=username, email=email, password=password)
        user.save()
        messages.success(request, "Registration successful. Please log in.")
        return redirect('login')
    return render(request, 'auth/register.html')

def login_redirect_view(request):
    """redirect to home"""
    return redirect('/')

def user_login(request):
    """login user"""
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        logger.info(f"Attempting login with username: {username}")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            logger.info(f"User {username} logged in successfully.")
            if user.is_student:
                return redirect('student_dashboard')
            elif user.is_teacher:
                return redirect('teacher_dashboard')
            else:
                return redirect('dashboardv1')
        else:
            logger.warning(f"Failed login attempt for username: {username}")
            return render(request, "auth/login.html", {"error_message": "Invalid username or password"})
    return render(request, 'auth/login.html')

@login_required
def user_logout(request):
    """logout user"""
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('login')

@login_required
def register_units(request):
    """register units for student"""
    if not request.user.is_student:
        return redirect('login')
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            registration = form.save(commit=False)
            registration.student = request.user
            registration.save()
            return redirect('student_dashboard')
    else:
        form = RegistrationForm()
    return render(request, 'portal/register_units.html', {'form': form})

def register_student(request, dojo_id=None):
    """register student with dojo from url"""
    selected_dojo = None
    if dojo_id:
        try:
            selected_dojo = Dojo.objects.get(id=dojo_id)
        except Dojo.DoesNotExist:
            messages.error(request, "The specified dojo was not found.")
            return redirect('login')
    if not selected_dojo:
        session_dojo_id = request.session.get('registration_dojo_id')
        registration_code = request.session.get('registration_code')
        if session_dojo_id:
            try:
                selected_dojo = Dojo.objects.get(id=session_dojo_id)
            except Dojo.DoesNotExist:
                pass
    if not selected_dojo and not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Please use a valid registration link or URL to sign up.")
        return redirect('login')
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            if selected_dojo:
                user.dojo = selected_dojo
                if registration_code:
                    try:
                        reg_link = DojoRegistrationLink.objects.get(code=registration_code)
                        user.registration_link = reg_link
                    except DojoRegistrationLink.DoesNotExist:
                        pass
            user.is_student = True
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, "Registration successful. Please log in.")
            request.session.pop('registration_dojo_id', None)
            request.session.pop('registration_code', None)
            return redirect('login')
    else:
        form = StudentRegistrationForm()
    context = {'form': form}
    if selected_dojo:
        context['dojo_name'] = selected_dojo.name
        context['dojo_id'] = selected_dojo.id
    return render(request, 'auth/register_student.html', context)

def register_teacher(request, dojo_id=None):
    """register teacher with dojo from url or form"""
    if not request.user.is_authenticated or (not request.user.is_staff and not request.user.is_superuser):
        messages.error(request, "You don't have permission to register instructors.")
        return redirect('login')
    selected_dojo = None
    if dojo_id:
        try:
            selected_dojo = Dojo.objects.get(id=dojo_id)
        except Dojo.DoesNotExist:
            messages.error(request, "The specified dojo was not found.")
    if request.method == 'POST':
        form = TeacherRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_teacher = True
            dojo_form_id = request.POST.get('dojo')
            if dojo_form_id:
                try:
                    user.dojo = Dojo.objects.get(id=dojo_form_id)
                except Dojo.DoesNotExist:
                    messages.error(request, "The selected dojo does not exist.")
                    return render(request, 'auth/register_teacher.html', {'form': form, 'dojos': Dojo.objects.all()})
            elif selected_dojo:
                user.dojo = selected_dojo
            elif request.user.dojo and not request.user.is_superuser:
                user.dojo = request.user.dojo
            user.save()
            messages.success(request, f"Instructor {user.get_full_name()} has been registered successfully.")
            return redirect('users_list')
    else:
        form = TeacherRegistrationForm()
    if request.user.is_superuser:
        dojos = Dojo.objects.all()
    elif request.user.dojo:
        dojos = Dojo.objects.filter(id=request.user.dojo.id)
    else:
        dojos = Dojo.objects.none()
    context = {
        'form': form, 
        'dojos': dojos,
        'selected_dojo': selected_dojo
    }
    return render(request, 'auth/register_teacher.html', context)

@login_required
def submit_assignment(request, event_id):
    """student submits assignment"""
    if not request.user.is_student:
        return redirect('login')
    assignment_event = get_object_or_404(
        TimelineEvent, 
        id=event_id, 
        student=request.user, 
        event_type='assignment'
    )
    if request.method == 'POST':
        assignment_event.is_submitted = True
        assignment_event.submission_notes = request.POST.get('notes', '')
        assignment_event.submission_date = timezone.now()
        if 'submission_file' in request.FILES:
            assignment_event.submission_file = request.FILES['submission_file']
        assignment_event.save()
        Submission.objects.create(
            assignment=assignment_event,
            student=request.user,
            file=request.FILES.get('submission_file'),
            notes=request.POST.get('notes', '')
        )
        messages.success(request, 'Assignment submitted successfully!')
        return redirect('assignments')
    return redirect('assignments')

@login_required
def students_in_unit(request, unit_id):
    """teacher views students in unit"""
    if not request.user.is_teacher:
        return redirect('login')
    unit = Unit.objects.get(id=unit_id)
    registrations = Registration.objects.filter(unit=unit)
    return render(request, 'portal/students_in_unit.html', {'unit': unit, 'registrations': registrations})

@login_required
def view_submissions(request, assignment_id):
    """teacher views submissions for assignment"""
    if not request.user.is_teacher:
        return redirect('login')
    assignment = Assignment.objects.get(id=assignment_id)
    submissions = Submission.objects.filter(assignment=assignment)
    return render(request, 'portal/view_submissions.html', {'assignment': assignment, 'submissions': submissions})

@login_required
def report_session(request):
    """student reports session"""
    if not request.user.is_student:
        return redirect('login')
    if request.method == 'POST':
        return redirect('student_dashboard')
    return render(request, 'portal/report_session.html')

# student dashboard
@login_required
def student_dashboard(request):
    """student dashboard main page"""
    if not request.user.is_student:
        return redirect('login')
    active_assignments = TimelineEvent.objects.filter(
        student=request.user,
        event_type='assignment',
        is_submitted=False
    ).order_by('due_date')
    active_count = active_assignments.count()
    overdue_count = active_assignments.filter(due_date__lt=timezone.now()).count()
    completed_count = TimelineEvent.objects.filter(
        student=request.user,
        event_type='assignment',
        is_submitted=True
    ).count()
    context = {
        'parent': 'dashboard',
        'segment': 'dashboardv1',
        'active_assignments': active_assignments,
        'active_count': active_count,
        'overdue_count': overdue_count,
        'completed_count': completed_count
    }
    context['notifications'] = request.user.notifications.filter(is_read=False)
    return render(request, 'pages/index.html', context)

# student progress
@login_required
def student_progress(request):
    """student progress page"""
    if not request.user.is_student:
        return redirect('login')
    progress_reports = TimelineEvent.objects.filter(
        student=request.user,
        event_type='progress_report'
    ).order_by('-created_at')
    completed_assignments = TimelineEvent.objects.filter(
        student=request.user,
        event_type='assignment',
        is_submitted=True
    ).count()
    total_assignments = TimelineEvent.objects.filter(
        student=request.user,
        event_type='assignment'
    ).count()
    completion_rate = 0
    if total_assignments > 0:
        completion_rate = (completed_assignments / total_assignments) * 100
    attendance_stats = Attendance.get_attendance_stats(request.user.id)
    achievement_criteria = [
      {"name": "Basics", "description": "Fundamental techniques", "threshold": 20, "color": "#4CAF50"},
      {"name": "Forms", "description": "Basic forms mastery", "threshold": 40, "color": "#2196F3"},
      {"name": "Sparring", "description": "Controlled sparring", "threshold": 60, "color": "#FF9800"},
      {"name": "Advanced", "description": "Advanced techniques", "threshold": 80, "color": "#9C27B0"},
      {"name": "Mastery", "description": "Complete belt level mastery", "threshold": 100, "color": "#F44336"}
    ]
    student_progress_value = 0 
    for criteria in achievement_criteria:
        criteria['achieved'] = student_progress_value >= criteria['threshold']
    context = {
        'progress_reports': progress_reports,
        'completion_rate': round(completion_rate),
        'completed_assignments': completed_assignments,
        'total_assignments': total_assignments,
        'attendance_stats': attendance_stats,
        'achievement_criteria': achievement_criteria,
        'student_progress_value': student_progress_value,
        'parent': 'progress',
        'segment': 'student_progress',
        'now': timezone.now(),
    }
    return render(request, 'pages/student_progress.html', context)

@login_required
def student_criteria(request):
    """student criteria progress page"""
    if not request.user.is_student:
        return redirect('login')
    progress_reports = TimelineEvent.objects.filter(
        student=request.user,
        event_type='progress_report'
    ).order_by('-created_at')
    completed_assignments = TimelineEvent.objects.filter(
        student=request.user,
        event_type='assignment',
        is_submitted=True
    ).count()
    total_assignments = TimelineEvent.objects.filter(
        student=request.user,
        event_type='assignment'
    ).count()
    completion_rate = 0
    if total_assignments > 0:
        completion_rate = (completed_assignments / total_assignments) * 100
    attendance_stats = Attendance.get_attendance_stats(request.user.id)
    achievement_criteria = [
      {"name": "Basics", "description": "Fundamental techniques", "threshold": 20, "color": "#4CAF50"},
      {"name": "Forms", "description": "Basic forms mastery", "threshold": 40, "color": "#2196F3"},
      {"name": "Sparring", "description": "Controlled sparring", "threshold": 60, "color": "#FF9800"},
      {"name": "Advanced", "description": "Advanced techniques", "threshold": 80, "color": "#9C27B0"},
      {"name": "Mastery", "description": "Complete belt level mastery", "threshold": 100, "color": "#F44336"}
    ]
    student_progress_value = 65 
    for criteria in achievement_criteria:
        criteria['achieved'] = student_progress_value >= criteria['threshold']
    context = {
        'progress_reports': progress_reports,
        'completion_rate': round(completion_rate),
        'completed_assignments': completed_assignments,
        'total_assignments': total_assignments,
        'attendance_stats': attendance_stats,
        'achievement_criteria': achievement_criteria,
        'student_progress_value': student_progress_value,
        'parent': 'progress',
        'segment': 'student_progress',
        'now': timezone.now(),
    }
    return render(request, 'pages/student_criteria.html', context)

@login_required
def view_assignment(request):
    """student views assignments"""
    if not request.user.is_student:
        return redirect('login')
    active_assignments = TimelineEvent.objects.filter(
        student=request.user,
        event_type='assignment',
        is_submitted=False
    ).order_by('due_date')
    completed_assignments = TimelineEvent.objects.filter(
        student=request.user,
        event_type='assignment',
        is_submitted=True
    ).order_by('-submission_date')
    timeline_events = TimelineEvent.objects.filter(
        student=request.user
    ).prefetch_related(
        'feedback',
        'feedback__author'
    ).order_by('-created_at')
    context = {
        'active_assignments': active_assignments,
        'completed_assignments': completed_assignments,
        'timeline_events': timeline_events
    }
    return render(request, 'pages/assignments.html', context)

@login_required
def view_assessment(request):
    """student views assessments"""
    if not request.user.is_student:
        return redirect('login')
    timeline_events = TimelineEvent.objects.filter(
        student=request.user
    ).prefetch_related(
        'feedback',
        'feedback__author'
    ).order_by('-created_at')
    context = {
        'timeline_events': timeline_events,
    }
    return render(request, 'pages/assessments.html', context)

@login_required
def progress_report(request):
    """student progress report page"""
    if not request.user.is_student:
        return redirect('login')
    return render(request, 'pages/student_progress.html')

@login_required
def teacher_dashboard(request):
    """teacher dashboard main page"""
    if not request.user.is_teacher:
        return redirect('login')
    units = Unit.objects.filter(teacher=request.user)
    return render(request, 'portal/teacher_dashboard.html', {'units': units})

@login_required
def post_assignment(request):
    """teacher posts assignment"""
    if not request.user.is_teacher:
        return redirect('login')
    if request.method == 'POST':
        unit_id = request.POST.get('unit')
        title = request.POST.get('title')
        description = request.POST.get('description')
        file = request.FILES['file']
        try:
            unit = Unit.objects.get(id=unit_id, teacher=request.user)
            Assignment.objects.create(unit=unit, title=title, description=description, file=file)
            return redirect('teacher_dashboard')
        except Unit.DoesNotExist:
            messages.error(request, "Invalid unit selected.")
            return redirect('post_assignment')
    units = Unit.objects.filter(teacher=request.user)
    logger.debug(f"Number of units: {units.count()}")
    logger.debug(f"Units: {units}")
    return render(request, 'portal/post_assignment.html', {'units': units})

@login_required
def admin_student_list(request, unit_id):
    """admin views students in unit"""
    if not request.user.is_staff:
        return redirect('admin:login')
    unit = get_object_or_404(Unit, id=unit_id)
    registrations = Registration.objects.filter(unit=unit).select_related('student')
    context = {
        'unit': unit,
        'registrations': registrations,
        'title': f'Students in {unit.name}',
        'parent': 'Students',
        'segment': 'student_list',
        'has_permission': True,
        'is_popup': False,
        'has_view_permission': True
    }
    return render(request, 'pages/instructor/student_list.html', context)

@login_required
def admin_student_info(request, student_id):
    """admin views student info"""
    if not request.user.is_staff:
        return redirect('admin:login')
    student = get_object_or_404(
        CustomUser.objects.prefetch_related(
            Prefetch(
                'timeline_events',
                queryset=TimelineEvent.objects.prefetch_related('submissions').order_by('-created_at')
            )
        ),
        id=student_id
    )
    active_count = TimelineEvent.objects.filter(
        student=student,
        event_type='assignment',
        is_submitted=False,
        due_date__gt=timezone.now()
    ).count()
    completed_count = TimelineEvent.objects.filter(
        student=student,
        event_type='assignment',
        is_submitted=True
    ).count()
    attendance_stats = Attendance.get_attendance_stats(student_id)
    attendance_count = attendance_stats['present'] + attendance_stats['late']
    total_classes = attendance_stats['total']
    context = {
        'student': student,
        'timeline_events': student.timeline_events.all(),
        'event_types': [
            ('assessment', 'fas fa-chart-bar', 'Assessment', 'warning'),
            ('assignment', 'fas fa-tasks', 'Assignment', 'success'),
            ('material', 'fas fa-book', 'Material', 'info')
        ],
        'title': f'Student Info - {student.get_full_name}',
        'active_count': active_count,
        'completed_count': completed_count,
        'total_assignments': active_count + completed_count,
        'attendance_count': attendance_count,
        'total_classes': total_classes,
        'attendance_stats': attendance_stats,
        'now': timezone.now(),
    }
    return render(request, 'pages/instructor/student_info.html', context)

@login_required
def event_detail_api(request, event_id):
    """api for event details"""
    try:
        event = TimelineEvent.objects.get(id=event_id)
        data = {
            'id': event.id,
            'title': event.title,
            'content': event.content,
            'event_type': event.event_type,
            'created_at': event.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'due_date': event.due_date.strftime('%Y-%m-%d %H:%M:%S') if event.due_date else None,
            'is_submitted': event.is_submitted
        }
        return JsonResponse(data)
    except TimelineEvent.DoesNotExist:
        return JsonResponse({'error': 'Event not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def change_belt(request, student_id):
    """change student belt level"""
    if not (request.user.is_staff or request.user.is_teacher):
        messages.error(request, "You don't have permission to change belt levels.")
        return redirect('admin_student_info', student_id=student_id)
    if request.method == 'POST':
        student = get_object_or_404(CustomUser, id=student_id)
        new_belt = request.POST.get('belt')
        if new_belt in dict(CustomUser.BELT_CHOICES):
            student.belt = new_belt
            student.save()
            messages.success(request, f"Belt level updated to {student.get_belt_display()}")
        else:
            messages.error(request, "Invalid belt level selected")
    return redirect('admin_student_info', student_id=student_id)

@login_required
def add_timeline_event(request, student_id):
    """add timeline event for student"""
    if not (request.user.is_staff or request.user.is_teacher):
        messages.error(request, "Permission denied")
        return redirect('admin_student_info', student_id=student_id)
    if request.method == 'POST':
        student = get_object_or_404(CustomUser, id=student_id)
        event_type = request.POST.get('event_type')
        title = request.POST.get('title')
        if 'strengths' in request.POST:
            event_type = 'progress_report'
            title = f"Progress Report - {timezone.now().strftime('%B %Y')}"
            strengths = request.POST.get('strengths', '')
            growth_areas = request.POST.get('growth_areas', '')
            next_steps = request.POST.get('next_steps', '')
            content = f"""
            <div class="progress-report-content">
                <div class="strengths-section">
                    <h4><i class="fas fa-star text-success mr-2"></i>Strengths</h4>
                    {strengths}
                </div>
                <div class="growth-section mt-4">
                    <h4><i class="fas fa-exclamation-circle text-warning mr-2"></i>Areas for Growth</h4>
                    {growth_areas}
                </div>
                <div class="next-steps-section mt-4">
                    <h4><i class="fas fa-route text-info mr-2"></i>Next Steps</h4>
                    {next_steps}
                </div>
            </div>
            """
            event = TimelineEvent.objects.create(
                student=student,
                event_type=event_type,
                title=title,
                content=content,
                created_by=request.user
            )
            Notification.objects.create(
                user=student,
                title="New Progress Report Available",
                message=f"Your instructor {request.user.get_full_name()} has posted a new progress report",
                notification_type='progress_report',
                link=f'/student_progress/#{event.id}'
            )
            messages.success(request, "Progress report added successfully")
            return redirect('admin_student_info', student_id=student_id)
        event = TimelineEvent.objects.create(
            student=student,
            event_type=event_type,
            title=title,
            content=request.POST.get('content'),
            created_by=request.user
        )
        if event_type == 'assignment':
            due_date = request.POST.get('due_date')
            event.due_date = timezone.make_aware(datetime.strptime(due_date, '%Y-%m-%d %H:%M:%S'))
        if event_type == 'assessment':
            event.assessment_result = request.POST.get('assessment_result')
        event.save()
        notification_data = {
            'assignment': {
                'title': 'New Assignment Posted',
                'message': f'A new assignment "{title}" has been posted by {request.user.get_full_name()}',
                'type': 'assignment'
            },
            'assessment': {
                'title': 'New Assessment Result',
                'message': f'Your assessment result for "{title}" has been posted',
                'type': 'assessment'
            },
            'material': {
                'title': 'New Learning Material Available',
                'message': f'New material "{title}" has been added to your course',
                'type': 'material'
            }
        }
        if event_type in notification_data:
            data = notification_data[event_type]
            Notification.objects.create(
                user=student,
                title=data['title'],
                message=data['message'],
                notification_type=data['type'],
                link=f'/assignments/#{event.id}'
            )
        messages.success(request, f"{event_type.title()} added successfully")
    return redirect('admin_student_info', student_id=student_id)

@login_required
def event_detail(request, event_id):
    """view or update event details"""
    event = get_object_or_404(TimelineEvent, id=event_id)
    if request.method == 'POST':
        if not (request.user.is_staff or request.user.is_teacher):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        event.title = request.POST.get('title', event.title)
        event.content = request.POST.get('content', event.content)
        if event.event_type == 'assignment':
            due_date = request.POST.get('due_date')
            if due_date:
                event.due_date = timezone.make_aware(datetime.strptime(due_date, '%Y-%m-%d %H:%M:%S'))
        event.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({
        'id': event.id,
        'title': event.title,
        'content': event.content,
        'event_type': event.event_type,
        'due_date': event.due_date.isoformat() if event.due_date else None,
    })

@login_required
def event_feedback(request, event_id):
    """add feedback to event"""
    event = get_object_or_404(TimelineEvent, id=event_id)
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            feedback = EventFeedback.objects.create(
                event=event,
                author=request.user,
                content=content
            )
            Notification.objects.create(
                user=event.student,
                title=f"New feedback on {event.title}",
                message=f"{request.user.get_full_name()} added feedback to your {event.get_event_type_display().lower()}",
                notification_type='feedback',
                link=f'/assignments/#{event.id}'
            )
            return JsonResponse({
                'status': 'success',
                'feedback': {
                    'id': feedback.id,
                    'content': feedback.content,
                    'created_at': feedback.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'author': feedback.author.get_full_name()
                }
            })
        return JsonResponse({'error': 'Content is required'}, status=400)
    feedback = event.feedback.select_related('author').all()
    return JsonResponse([{
        'id': f.id,
        'content': f.content,
        'created_at': f.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'user': f.author.get_full_name()
    } for f in feedback], safe=False)

def register_v1(request):
    """register v1 page"""
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            logger.info('Account created successfully!')
            return redirect('/accounts/login/')
        else:
            logger.warning("Registration failed!")
    else:
        form = RegistrationForm()
    context = {'form': form}
    return render(request, 'pages/examples/register.html', context)

def register_v2(request):
    """register v2 page"""
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            logger.info('Account created successfully!')
            return redirect('/accounts/login/')
        else:
            logger.warning("Registration failed!")
    else:
        form = RegistrationForm()
    context = {'form': form}
    return render(request, 'pages/examples/register-v2.html', context)

class UserLoginView(auth_views.LoginView):
    """user login view"""
    template_name = 'accounts/login.html'
    form_class = LoginForm
    success_url = '/'

class UserLoginViewV1(auth_views.LoginView):
    """user login view v1"""
    template_name = 'pages/examples/login.html'
    form_class = LoginForm
    success_url = '/'

class UserLoginViewV2(auth_views.LoginView):
    """user login view v2"""
    template_name = 'pages/examples/login-v2.html'
    form_class = LoginForm
    success_url = '/'

class UserPasswordResetView(auth_views.PasswordResetView):
    """password reset view"""
    template_name = 'accounts/forgot-password.html'
    form_class = UserPasswordResetForm

class UserPasswordResetViewV1(auth_views.PasswordResetView):
    """password reset view v1"""
    template_name = 'pages/examples/forgot-password.html'
    form_class = UserPasswordResetForm

class UserPasswordResetViewV2(auth_views.PasswordResetView):
    """password reset view v2"""
    template_name = 'pages/examples/forgot-password-v2.html'
    form_class = UserPasswordResetForm

class UserPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    """password reset confirm view"""
    template_name = 'accounts/recover-password.html'
    form_class = UserSetPasswordForm

class UserPasswordChangeView(auth_views.PasswordChangeView):
    """password change view"""
    template_name = 'accounts/password_change.html'
    form_class = UserPasswordChangeForm

class UserPasswordChangeViewV1(auth_views.PasswordChangeView):
    """password change view v1"""
    template_name = 'pages/examples/recover-password.html'
    form_class = UserPasswordChangeForm

class UserPasswordChangeViewV2(auth_views.PasswordChangeView):
    """password change view v2"""
    template_name = 'pages/examples/recover-password-v2.html'
    form_class = UserPasswordChangeForm

def user_logout_view(request):
    """logout view"""
    logout(request)
    return redirect('/accounts/login/')

def index(request):
    """dashboard index page"""
    context = {
        'parent': 'dashboard',
        'segment': 'dashboardv1'
    }
    return render(request, 'pages/index.html', context)

def index2(request):
    """dashboard index2 page"""
    context = {
        'parent': 'dashboard',
        'segment': 'dashboardv2'
    }
    return render(request, 'pages/index2.html', context)

def index3(request):
    """dashboard index3 page"""
    context = {
        'parent': 'dashboard',
        'segment': 'dashboardv3'
    }
    return render(request, 'pages/index3.html', context)

def widgets(request):
    """widgets page"""
    context = {
        'parent': '',
        'segment': 'widgets'
    }
    return render(request, 'pages/widgets.html', context)

def examples_calendar(request):
    """examples calendar page"""
    context = {
        'parent': '',
        'segment': 'calendar'
    }
    return render(request, 'pages/calendar.html', context)

def examples_gallery(request):
    """examples gallery page"""
    context = {
        'parent': '',
        'segment': 'gallery'
    }
    return render(request, 'pages/gallery.html', context)

def examples_kanban(request):
    """examples kanban page"""
    context = {
        'parent': '',
        'segment': 'kanban_board'
    }
    return render(request, 'pages/kanban.html', context)

def mailbox_inbox(request):
    """mailbox inbox page"""
    context = {
        'parent': 'mailbox',
        'segment': 'inbox'
    }
    return render(request, 'pages/mailbox/mailbox.html', context)

def mailbox_compose(request):
    """mailbox compose page"""
    context = {
        'parent': 'mailbox',
        'segment': 'compose'
    }
    return render(request, 'pages/mailbox/compose.html', context)

def mailbox_read_mail(request):
    """mailbox read mail page"""
    context = {
        'parent': 'mailbox',
        'segment': 'read_mail'
    }
    return render(request, 'pages/mailbox/read-mail.html', context)

def examples_invoice(request):
    """examples invoice page"""
    context = {
        'parent': 'pages',
        'segment': 'invoice'
    }
    return render(request, 'pages/examples/invoice.html', context)

def invoice_print(request):
    """invoice print page"""
    context = {
        'parent': 'pages',
        'segment': 'invoice_print'
    }
    return render(request, 'pages/examples/invoice-print.html', context)

def examples_profile(request):
    """examples profile page"""
    context = {
        'parent': 'pages',
        'segment': 'profile'
    }
    return render(request, 'pages/examples/profile.html', context)

def examples_e_commerce(request):
    """examples e-commerce page"""
    context = {
        'parent': 'pages',
        'segment': 'ecommerce'
    }
    return render(request, 'pages/examples/e-commerce.html', context)

def examples_projects(request):
    """examples projects page"""
    context = {
        'parent': 'pages',
        'segment': 'projects'
    }
    return render(request, 'pages/examples/projects.html', context)

def examples_project_add(request):
    """examples project add page"""
    context = {
        'parent': 'pages',
        'segment': 'project_add'
    }
    return render(request, 'pages/examples/project-add.html', context)

def examples_project_edit(request):
    """examples project edit page"""
    context = {
        'parent': 'pages',
        'segment': 'project_edit'
    }
    return render(request, 'pages/examples/project-edit.html', context)

def examples_project_detail(request):
    """examples project detail page"""
    context = {
        'parent': 'pages',
        'segment': 'project_detail'
    }
    return render(request, 'pages/examples/project-detail.html', context)

def examples_contacts(request):
    """examples contacts page"""
    context = {
        'parent': 'pages',
        'segment': 'contacts'
    }
    return render(request, 'pages/examples/contacts.html', context)

def examples_faq(request):
    """examples faq page"""
    context = {
        'parent': 'pages',
        'segment': 'faq'
    }
    return render(request, 'pages/examples/faq.html', context)

def examples_contact_us(request):
    """examples contact us page"""
    context = {
        'parent': 'pages',
        'segment': 'contact_us'
    }
    return render(request, 'pages/examples/contact-us.html', context)

def lockscreen(request):
    """lockscreen page"""
    context = {
        'parent': '',
        'segment': ''
    }
    return render(request, 'pages/examples/lockscreen.html', context)

def legacy_user_menu(request):
    """legacy user menu page"""
    context = {
        'parent': 'extra',
        'segment': 'legacy_user'
    }
    return render(request, 'pages/examples/legacy-user-menu.html', context)

def language_menu(request):
    """language menu page"""
    context = {
        'parent': 'extra',
        'segment': 'legacy_menu'
    }
    return render(request, 'pages/examples/language-menu.html', context)

def error_404(request):
    """error 404 page"""
    context = {
        'parent': 'extra',
        'segment': 'error_404'
    }
    return render(request, 'pages/examples/404.html', context)

def error_500(request):
    """error 500 page"""
    context = {
        'parent': 'extra',
        'segment': 'error_500'
    }
    return render(request, 'pages/examples/500.html', context)

def pace(request):
    """pace page"""
    context = {
        'parent': 'extra',
        'segment': 'pace'
    }
    return render(request, 'pages/examples/pace.html', context)

def blank_page(request):
    """blank page"""
    context = {
        'parent': 'extra',
        'segment': 'blank_page'
    }
    return render(request, 'pages/examples/blank.html', context)

def starter_page(request):
    """starter page"""
    context = {
        'parent': 'extra',
        'segment': 'starter_page'
    }
    return render(request, 'pages/examples/starter.html', context)

def search_simple(request):
    """search simple page"""
    context = {
        'parent': 'search',
        'segment': 'search_simple'
    }
    return render(request, 'pages/search/simple.html', context)

def search_enhanced(request):
    """search enhanced page"""
    context = {
        'parent': 'search',
        'segment': 'search_enhanced'
    }
    return render(request, 'pages/search/enhanced.html', context)

def simple_results(request):
    """simple results page"""
    context = {
        'parent': '',
        'segment': ''
    }
    return render(request, 'pages/search/simple-results.html', context)

def enhanced_results(request):
    """enhanced results page"""
    context = {
        'parent': '',
        'segment': ''
    }
    return render(request, 'pages/search/enhanced-results.html', context)

def iframe(request):
    """iframe page"""
    context = {
        'parent': '',
        'segment': ''
    }
    return render(request, 'pages/search/iframe.html', context)

def chartjs(request):
    """chartjs page"""
    context = {
        'parent': 'charts',
        'segment': 'chartjs'
    }
    return render(request, 'pages/charts/chartjs.html', context)

def flot(request):
    """flot page"""
    context = {
        'parent': 'charts',
        'segment': 'flot'
    }
    return render(request, 'pages/charts/flot.html', context)

def inline(request):
    """inline page"""
    context = {
        'parent': 'charts',
        'segment': 'inline'
    }
    return render(request, 'pages/charts/inline.html', context)

def uplot(request):
    """uplot page"""
    context = {
        'parent': 'charts',
        'segment': 'uplot'
    }
    return render(request, 'pages/charts/uplot.html', context)

def profile(request):
    """profile page"""
    context = {
        'parent': 'pages',
        'segment': 'profile'
    }
    return render(request, 'pages/examples/profile.html', context)

def top_navigation(request):
    """top navigation layout"""
    context = {
        'parent': 'layout',
        'segment': 'top_navigation'
    }
    return render(request, 'pages/layout/top-nav.html', context)

def top_nav_sidebar(request):
    """top navigation with sidebar layout"""
    context = {
        'parent': 'layout',
        'segment': 'top navigation with sidebar'
    }
    return render(request, 'pages/layout/top-nav-sidebar.html', context)

def boxed(request):
    """boxed layout"""
    context = {
        'parent': 'layout',
        'segment': 'boxed_layout'
    }
    return render(request, 'pages/layout/boxed.html', context)

def fixed_sidebar(request):
    """fixed sidebar layout"""
    context = {
        'parent': 'layout',
        'segment': 'fixed_layout'
    }
    return render(request, 'pages/layout/fixed-sidebar.html', context)

def fixed_sidebar_custom(request):
    """fixed sidebar custom layout"""
    context = {
        'parent': 'layout',
        'segment': 'layout_cuastom'
    }
    return render(request, 'pages/layout/fixed-sidebar-custom.html', context)

def fixed_topnav(request):
    """fixed top navigation layout"""
    context = {
        'parent': 'layout',
        'segment': 'fixed_topNav'
    }
    return render(request, 'pages/layout/fixed-topnav.html', context)

def fixed_footer(request):
    """fixed footer layout"""
    context = {
        'parent': 'layout',
        'segment': 'fixed_footer'
    }
    return render(request, 'pages/layout/fixed-footer.html', context)

def collapsed_sidebar(request):
    """collapsed sidebar layout"""
    context = {
        'parent': 'layout',
        'segment': 'collapsed_sidebar'
    }
    return render(request, 'pages/layout/collapsed-sidebar.html', context)

def ui_general(request):
    """ui general page"""
    context = {
        'parent': 'ui',
        'segment': 'general'
    }
    return render(request, 'pages/UI/general.html', context)

def ui_icons(request):
    """ui icons page"""
    context = {
        'parent': 'ui',
        'segment': 'icons'
    }
    return render(request, 'pages/UI/icons.html', context)

def ui_buttons(request):
    """ui buttons page"""
    context = {
        'parent': 'ui',
        'segment': 'buttons'
    }
    return render(request, 'pages/UI/buttons.html', context)

def ui_sliders(request):
    """ui sliders page"""
    context = {
        'parent': 'ui',
        'segment': 'sliders'
    }
    return render(request, 'pages/UI/sliders.html', context)

def ui_modals_alerts(request):
    """ui modals and alerts page"""
    context = {
        'parent': 'ui',
        'segment': 'modals_alerts'
    }
    return render(request, 'pages/UI/modals.html', context)

def ui_navbar_tabs(request):
    """ui navbar and tabs page"""
    context = {
        'parent': 'ui',
        'segment': 'navbar_tabs'
    }
    return render(request, 'pages/UI/navbar.html', context)

def ui_timeline(request):
    """ui timeline page"""
    context = {
        'parent': 'ui',
        'segment': 'timeline'
    }
    return render(request, 'pages/UI/timeline.html', context)

def ui_ribbons(request):
    """ui ribbons page"""
    context = {
        'parent': 'ui',
        'segment': 'ribbons'
    }
    return render(request, 'pages/UI/ribbons.html', context)

def form_general(request):
    """form general page"""
    context = {
        'parent': 'forms',
        'segment': 'form_general'
    }
    return render(request, 'pages/forms/general.html', context)

def form_advanced(request):
    """form advanced page"""
    context = {
        'parent': 'forms',
        'segment': 'advanced_form'
    }
    return render(request, 'pages/forms/advanced.html', context)

def form_editors(request):
    """form editors page"""
    context = {
        'parent': 'forms',
        'segment': 'text_editors'
    }
    return render(request, 'pages/forms/editors.html', context)

def form_validation(request):
    """form validation page"""
    context = {
        'parent': 'forms',
        'segment': 'validation'
    }
    return render(request, 'pages/forms/validation.html', context)

def table_simple(request):
    """simple table page"""
    context = {
        'parent': 'tables',
        'segment': 'simple_table'
    }
    return render(request, 'pages/tables/simple.html', context)

def table_data(request):
    """data table page"""
    context = {
        'parent': 'tables',
        'segment': 'data_table'
    }
    return render(request, 'pages/tables/data.html', context)

def table_jsgrid(request):
    """jsgrid table page"""
    context = {
        'parent': 'tables',
        'segment': 'jsGrid'
    }
    return render(request, 'pages/tables/jsgrid.html', context)

@login_required
def dismiss_notification(request, notification_id):
    """dismiss notification"""
    if request.method == 'POST':
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def take_attendance(request, unit_id):
    """take attendance for unit"""
    if not (request.user.is_staff or request.user.is_teacher):
        messages.error(request, "Permission denied")
        return redirect('dashboardv1')
    unit = get_object_or_404(Unit, id=unit_id)
    registrations = Registration.objects.filter(unit=unit).select_related('student')
    context = {
        'unit': unit,
        'registrations': registrations,
        'today': timezone.now().date(),
    }
    return render(request, 'pages/instructor/take_attendance.html', context)

@login_required
def save_attendance(request):
    """save attendance records"""
    if not (request.user.is_staff or request.user.is_teacher):
        messages.error(request, "Permission denied")
        return redirect('dashboardv1')
    if request.method == "POST":
        unit_id = request.POST.get('unit_id')
        unit = get_object_or_404(Unit, id=unit_id)
        attendance_date = request.POST.get('attendance_date')
        student_records = {}
        for key, value in request.POST.items():
            if key.startswith('student_'):
                student_id = key.replace('student_', '')
                notes = request.POST.get(f'notes_{student_id}', '')
                student_records[student_id] = {'status': value, 'notes': notes}
        attendance_count = 0
        for student_id, data in student_records.items():
            try:
                student = CustomUser.objects.get(id=student_id)
                attendance, created = Attendance.objects.update_or_create(
                    student=student,
                    unit=unit,
                    date=attendance_date,
                    defaults={
                        'status': data['status'],
                        'notes': data['notes'],
                        'marked_by': request.user
                    }
                )
                attendance_count += 1
                if created:
                    status_text = dict(Attendance.ATTENDANCE_STATUS).get(data['status'], data['status'])
                    title = f"Attendance Marked: {status_text}"
                    TimelineEvent.objects.create(
                        student=student,
                        event_type='join',
                        title=title,
                        content=f"Attendance for {unit.name} on {attendance_date}: {status_text}",
                        created_by=request.user
                    )
            except CustomUser.DoesNotExist:
                continue
        messages.success(request, f"Attendance saved successfully for {attendance_count} students.")
        return redirect('admin_student_list', unit_id=unit_id)
    messages.error(request, "Invalid request method")
    return redirect('dashboardv1')

@login_required
def attendance_list(request):
    """attendance dashboard listing"""
    if not (request.user.is_staff or request.user.is_teacher):
        messages.error(request, "Permission denied")
        return redirect('dashboardv1')
    if request.user.is_staff and not request.user.is_teacher:
        units = Unit.objects.all().order_by('name')
    else:
        units = Unit.objects.filter(teacher=request.user).order_by('name')
    recent_attendance = Attendance.objects.select_related(
        'student', 'unit', 'marked_by'
    ).order_by('-date', '-created_at')[:30]
    attendance_by_day = {}
    for attendance in recent_attendance:
        day_key = str(attendance.date)
        if day_key not in attendance_by_day:
            attendance_by_day[day_key] = {
                'date': attendance.date,
                'units': {}
            }
        unit_key = attendance.unit.id
        if unit_key not in attendance_by_day[day_key]['units']:
            attendance_by_day[day_key]['units'][unit_key] = {
                'unit': attendance.unit,
                'present': 0,
                'absent': 0,
                'late': 0,
                'total': 0,
            }
        attendance_by_day[day_key]['units'][unit_key][attendance.status] += 1
        attendance_by_day[day_key]['units'][unit_key]['total'] += 1
    context = {
        'units': units,
        'recent_attendance': recent_attendance,
        'attendance_by_day': attendance_by_day,
        'parent': 'attendance',
        'segment': 'attendance_list',
        'title': 'Attendance Records',
    }
    return render(request, 'pages/instructor/attendance_list.html', context)

@login_required
def attendance_records(request, unit_id):
    """detailed attendance records for unit"""
    if not (request.user.is_staff or request.user.is_teacher):
        messages.error(request, "Permission denied")
        return redirect('dashboardv1')
    unit = get_object_or_404(Unit, id=unit_id)
    attendance_dates = Attendance.objects.filter(
        unit=unit
    ).values('date').distinct().order_by('-date')
    attendance_data = {}
    for date_obj in attendance_dates:
        date = date_obj['date']
        records = Attendance.objects.filter(
            unit=unit, 
            date=date
        ).select_related('student')
        attendance_data[str(date)] = {
            'date': date,
            'records': records,
            'summary': {
                'present': records.filter(status='present').count(),
                'absent': records.filter(status='absent').count(),
                'late': records.filter(status='late').count(),
                'total': records.count(),
            }
        }
    context = {
        'unit': unit,
        'attendance_data': attendance_data,
        'parent': 'attendance',
        'segment': 'attendance_records',
        'title': f'Attendance Records: {unit.name}',
    }
    return render(request, 'pages/instructor/attendance_records.html', context)

@login_required
def edit_attendance(request, attendance_id):
    """edit attendance record"""
    if not (request.user.is_staff or request.user.is_teacher):
        messages.error(request, "Permission denied")
        return redirect('dashboardv1')
    attendance = get_object_or_404(Attendance, id=attendance_id)
    if request.method == "POST":
        status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        if status in dict(Attendance.ATTENDANCE_STATUS).keys():
            attendance.status = status
            attendance.notes = notes
            attendance.marked_by = request.user
            attendance.save()
            messages.success(request, "Attendance record updated successfully")
            return redirect('attendance_records', unit_id=attendance.unit.id)
        else:
            messages.error(request, "Invalid status selected")
    context = {
        'attendance': attendance,
        'statuses': Attendance.ATTENDANCE_STATUS,
        'parent': 'attendance',
        'segment': 'edit_attendance',
        'title': f'Edit Attendance: {attendance.student.get_full_name()}',
    }
    return render(request, 'pages/instructor/edit_attendance.html', context)

@login_required
def manage_feedback_templates(request):
    """view and add feedback templates"""
    if not (request.user.is_staff or request.user.is_teacher):
        messages.error(request, "Permission denied")
        return redirect('dashboardv1')
    templates = FeedbackTemplate.objects.filter(created_by=request.user).order_by('category', 'title')
    if request.method == "POST":
        title = request.POST.get('title')
        content = request.POST.get('content')
        category = request.POST.get('category')
        if title and content:
            FeedbackTemplate.objects.create(
                title=title,
                content=content,
                category=category,
                created_by=request.user
            )
            messages.success(request, "Feedback template created successfully")
            return redirect('manage_feedback_templates')
        else:
            messages.error(request, "Title and content are required")
    context = {
        'templates': templates,
        'categories': FeedbackTemplate.CATEGORY_CHOICES,
        'title': 'Manage Feedback Templates',
        'parent': 'settings',
        'segment': 'feedback_templates',
    }
    return render(request, 'pages/instructor/manage_feedback_templates.html', context)

@login_required
def edit_feedback_template(request, template_id):
    """edit feedback template"""
    if not (request.user.is_staff or request.user.is_teacher):
        messages.error(request, "Permission denied")
        return redirect('dashboardv1')
    template = get_object_or_404(FeedbackTemplate, id=template_id, created_by=request.user)
    if request.method == "POST":
        title = request.POST.get('title')
        content = request.POST.get('content')
        category = request.POST.get('category')
        if title and content:
            template.title = title
            template.content = content
            template.category = category
            template.save()
            messages.success(request, "Feedback template updated successfully")
            return redirect('manage_feedback_templates')
        else:
            messages.error(request, "Title and content are required")
    context = {
        'template': template,
        'categories': FeedbackTemplate.CATEGORY_CHOICES,
        'title': 'Edit Feedback Template',
        'parent': 'settings',
        'segment': 'feedback_templates',
    }
    return render(request, 'pages/edit_feedback_template.html', context)

@login_required
def delete_feedback_template(request, template_id):
    """delete feedback template"""
    if not (request.user.is_staff or request.user.is_teacher):
        messages.error(request, "Permission denied")
        return redirect('dashboardv1')
    template = get_object_or_404(FeedbackTemplate, id=template_id, created_by=request.user)
    if request.method == "POST":
        template.delete()
        messages.success(request, "Feedback template deleted successfully")
        return redirect('manage_feedback_templates')
    return redirect('manage_feedback_templates')

@login_required
def get_feedback_templates(request):
    """api to get feedback templates"""
    if not (request.user.is_staff or request.user.is_teacher):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    templates = FeedbackTemplate.objects.filter(created_by=request.user).order_by('category', 'title')
    templates_by_category = {}
    for template in templates:
        category_name = dict(FeedbackTemplate.CATEGORY_CHOICES).get(template.category, 'Other')
        if category_name not in templates_by_category:
            templates_by_category[category_name] = []
        templates_by_category[category_name].append({
            'id': template.id,
            'title': template.title,
            'content': template.content,
        })
    return JsonResponse({'categories': templates_by_category})

@login_required
def manage_belt_criteria(request):
    """manage criteria for belt levels"""
    if not (request.user.is_staff or request.user.is_teacher):
        messages.error(request, "Permission denied")
        return redirect('dashboardv1')
    belt_choices = dict(CustomUser.BELT_CHOICES)
    criteria_by_belt = {}
    for belt_value, belt_name in CustomUser.BELT_CHOICES:
        criteria_by_belt[belt_value] = {
            'name': belt_name,
            'criteria': BeltCriteria.objects.filter(belt=belt_value).order_by('order', 'title')
        }
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_criteria':
            belt = request.POST.get('belt')
            title = request.POST.get('title')
            description = request.POST.get('description')
            order = request.POST.get('order', 0)
            try:
                order = int(order)
            except (ValueError, TypeError):
                order = 0
            if not title:
                messages.error(request, "Title is required")
                return redirect('manage_belt_criteria')
            if belt == 'all':
                for belt_value, _ in CustomUser.BELT_CHOICES:
                    BeltCriteria.objects.create(
                        belt=belt_value,
                        title=title,
                        description=description,
                        all_belts=False,
                        order=order,
                        created_by=request.user
                    )
                messages.success(request, f"Criteria '{title}' added to all belt levels")
            else:
                BeltCriteria.objects.create(
                    belt=belt,
                    title=title,
                    description=description,
                    all_belts=False,
                    order=order,
                    created_by=request.user
                )
                messages.success(request, f"Criteria '{title}' added successfully")
            return redirect('manage_belt_criteria')
        elif action == 'delete_criteria':
            criteria_id = request.POST.get('criteria_id')
            try:
                criteria = BeltCriteria.objects.get(id=criteria_id)
                title = criteria.title
                criteria.delete()
                messages.success(request, f"Criteria '{title}' deleted successfully")
            except BeltCriteria.DoesNotExist:
                messages.error(request, "Criteria not found")
            return redirect('manage_belt_criteria')
    context = {
        'criteria_by_belt': criteria_by_belt,
        'belt_choices': CustomUser.BELT_CHOICES,
        'parent': 'settings',
        'segment': 'belt_criteria',
        'title': 'Manage Belt Criteria'
    }
    return render(request, 'pages/instructor/manage_belt_criteria.html', context)

@login_required
def edit_belt_criteria(request, criteria_id):
    """edit belt criteria"""
    if not (request.user.is_staff or request.user.is_teacher):
        messages.error(request, "Permission denied")
        return redirect('dashboardv1')
    criteria = get_object_or_404(BeltCriteria, id=criteria_id)
    if request.method == 'POST':
        criteria.belt = request.POST.get('belt', criteria.belt)
        criteria.title = request.POST.get('title', criteria.title)
        criteria.description = request.POST.get('description', criteria.description)
        criteria.all_belts = request.POST.get('all_belts') == 'on'
        try:
            criteria.order = int(request.POST.get('order', criteria.order))
        except (ValueError, TypeError):
            pass
        criteria.save()
        messages.success(request, f"Criteria '{criteria.title}' updated successfully")
        return redirect('manage_belt_criteria')
    context = {
        'criteria': criteria,
        'belt_choices': CustomUser.BELT_CHOICES,
        'parent': 'settings',
        'segment': 'belt_criteria',
        'title': 'Edit Belt Criteria'
    }
    return render(request, 'pages/instructor/edit_belt_criteria.html', context)

@login_required
def update_student_criteria(request, student_id):
    """update student criteria completion"""
    if not (request.user.is_staff or request.user.is_teacher):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)
    student = get_object_or_404(CustomUser, id=student_id)
    criteria_id = request.POST.get('criteria_id')
    completed = request.POST.get('completed') == 'true'
    notes = request.POST.get('notes', '')
    criteria = get_object_or_404(BeltCriteria, id=criteria_id)
    progress, created = StudentCriteriaProgress.objects.update_or_create(
        student=student,
        criteria=criteria,
        defaults={
            'completed': completed,
            'completed_date': timezone.now() if completed else None,
            'completed_by': request.user if completed else None,
            'notes': notes
        }
    )
    belt_criteria_count = BeltCriteria.objects.filter(
        models.Q(belt=student.belt) | models.Q(all_belts=True)
    ).count()
    completed_count = StudentCriteriaProgress.objects.filter(
        student=student,
        criteria__in=BeltCriteria.objects.filter(
            models.Q(belt=student.belt) | models.Q(all_belts=True)
        ),
        completed=True
    ).count()
    progress_percent = 0
    if belt_criteria_count > 0:
        progress_percent = int((completed_count / belt_criteria_count) * 100)
    return JsonResponse({
        'success': True,
        'completed': progress.completed,
        'progress_percent': progress_percent
    })

@login_required
def get_student_criteria(request, student_id):
    """get student criteria and progress"""
    if not (request.user.is_staff or request.user.is_teacher):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    student = get_object_or_404(CustomUser, id=student_id)
    belt_criteria = BeltCriteria.objects.filter(
        models.Q(belt=student.belt) | models.Q(all_belts=True)
    ).order_by('order', 'title')
    progress_map = {
        p.criteria_id: p for p in StudentCriteriaProgress.objects.filter(
            student=student,
            criteria__in=belt_criteria
        )
    }
    criteria_data = []
    completed_count = 0
    total_count = len(belt_criteria)
    for criteria in belt_criteria:
        progress = progress_map.get(criteria.id)
        completed = progress and progress.completed
        if completed:
            completed_count += 1
        criteria_data.append({
            'id': criteria.id,
            'title': criteria.title,
            'description': criteria.description,
            'completed': completed,
            'notes': progress.notes if progress else '',
            'completed_date': progress.completed_date.strftime('%Y-%m-%d %H:%M:%S') if progress and progress.completed_date else None,
            'completed_by': progress.completed_by.get_full_name() if progress and progress.completed_by else None
        })
    progress_percent = 0
    if total_count > 0:
        progress_percent = int((completed_count / total_count) * 100)
    return JsonResponse({
        'criteria': criteria_data,
        'progress_percent': progress_percent,
        'belt': student.belt,
        'belt_name': student.get_belt_display()
    })

@login_required
def student_criteria(request):
    """student criteria progress page"""
    if not request.user.is_student:
        return redirect('login')
    progress_reports = TimelineEvent.objects.filter(
        student=request.user,
        event_type='progress_report'
    ).order_by('-created_at')
    completed_assignments = TimelineEvent.objects.filter(
        student=request.user,
        event_type='assignment',
        is_submitted=True
    ).count()
    total_assignments = TimelineEvent.objects.filter(
        student=request.user,
        event_type='assignment'
    ).count()
    completion_rate = 0
    if total_assignments > 0:
        completion_rate = (completed_assignments / total_assignments) * 100
    attendance_stats = Attendance.get_attendance_stats(request.user.id)
    belt_criteria = BeltCriteria.objects.filter(
        models.Q(belt=request.user.belt) | models.Q(all_belts=True)
    ).order_by('order', 'title')
    progress_map = {
        p.criteria_id: p for p in StudentCriteriaProgress.objects.filter(
            student=request.user,
            criteria__in=belt_criteria
        )
    }
    criteria_list = []
    completed_criteria = []
    incomplete_criteria = []
    completed_count = 0
    for criteria in belt_criteria:
        progress = progress_map.get(criteria.id)
        completed = progress and progress.completed
        criteria_info = {
            'id': criteria.id,
            'title': criteria.title,
            'description': criteria.description,
            'completed': completed,
            'notes': progress.notes if progress else '',
            'completed_date': progress.completed_date if progress and progress.completed_date else None,
            'threshold': 0
        }
        if completed:
            completed_count += 1
            completed_criteria.append(criteria_info)
        else:
            incomplete_criteria.append(criteria_info)
        criteria_list.append(criteria_info)
    total_count = len(belt_criteria)
    progress_percent = 0
    if total_count > 0:
        progress_percent = int((completed_count / total_count) * 100)
        for i, criteria in enumerate(criteria_list):
            criteria['threshold'] = int((i + 1) * (100 / total_count))
            criteria['color'] = f"hsl({120 * (i / total_count)}, 80%, 45%)"
    context = {
        'progress_reports': progress_reports,
        'completion_rate': round(completion_rate),
        'completed_assignments': completed_assignments,
        'total_assignments': total_assignments,
        'attendance_stats': attendance_stats,
        'criteria_list': criteria_list,
        'completed_criteria': completed_criteria,
        'incomplete_criteria': incomplete_criteria,
        'student_progress_value': progress_percent,
        'total_criteria': total_count,
        'completed_criteria_count': completed_count,
        'parent': 'progress',
        'segment': 'student_criteria',
        'now': timezone.now(),
    }
    return render(request, 'pages/student_criteria.html', context)

@login_required
def calendar(request):
    """enhanced calendar view"""
    is_student = request.user.is_student
    can_manage = (request.user.is_staff or request.user.is_teacher)
    if not (can_manage or is_student):
        messages.error(request, "Permission denied")
        return redirect('dashboardv1')
    birthdays_enabled = cache.get('birthday_events_enabled', True)
    context = {
        'parent': 'calendar',
        'segment': 'calendar',
        'title': 'Calendar',
        'birthdays_enabled': birthdays_enabled,
        'can_manage': can_manage,
        'is_student': is_student
    }
    return render(request, 'pages/instructor/calendar.html', context)

@login_required
def calendar_events(request):
    """api to get calendar events"""
    if not (request.user.is_staff or request.user.is_teacher or request.user.is_student):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    birthdays_enabled = cache.get('birthday_events_enabled', True)
    if not birthdays_enabled:
        events = CalendarEvent.objects.filter(is_birthday=False)
    else:
        events = CalendarEvent.objects.all()
        if not CalendarEvent.objects.filter(is_birthday=True).exists():
            CalendarEvent.generate_birthday_events()
    if request.user.is_student:
        visible_events = []
        for event in events:
            if event.is_visible_to_user(request.user):
                visible_events.append(event)
        events = visible_events
    event_list = []
    for event in events:
        start = localtime(event.start_time)
        event_data = {
            'id': event.id,
            'title': event.title,
            'start': start.isoformat(),
            'backgroundColor': event.background_color,
            'borderColor': event.background_color,
            'allDay': event.all_day,
            'extendedProps': {
                'description': event.description,
                'isBirthday': event.is_birthday,
                'repeats': event.repeats,
                'isAutoGenerated': event.is_auto_generated
            }
        }
        if event.end_time:
            end = localtime(event.end_time)
            event_data['end'] = end.isoformat()
        if event.repeats and event.repeat_until:
            start = localtime(event.start_time)
            end = localtime(event.end_time) if event.end_time else None
            day_of_week = event.start_time.weekday()
            day_of_week = (day_of_week + 1) % 7
            event_data['startTime'] = start.strftime('%H:%M:%S')
            if end:
                event_data['endTime'] = end.strftime('%H:%M:%S')
            event_data['daysOfWeek'] = [day_of_week]
            event_data['startRecur'] = start.strftime('%Y-%m-%d')
            event_data['endRecur'] = event.repeat_until.strftime('%Y-%m-%d')
            if event.end_time and not event.all_day:
                duration_ms = int((event.end_time - event.start_time).total_seconds() * 1000)
                event_data['duration'] = str(duration_ms)
        event_list.append(event_data)
    return JsonResponse(event_list, safe=False)

@login_required
def calendar_event_detail(request, event_id):
    """api for calendar event details"""
    if not (request.user.is_staff or request.user.is_teacher):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    try:
        event = CalendarEvent.objects.get(id=event_id)
        start = localtime(event.start_time)
        if request.method == 'GET':
            visible_classes = list(event.visible_to_classes.values_list('id', flat=True))
            visible_students = list(event.visible_to_students.values_list('id', flat=True))
            data = {
                'id': event.id,
                'title': event.title,
                'description': event.description,
                'start': start.isoformat(),
                'end': event.end_time.isoformat() if event.end_time else None,
                'allDay': event.all_day,
                'backgroundColor': event.background_color,
                'repeats': event.repeats,
                'repeatUntil': event.repeat_until.isoformat() if event.repeat_until else None,
                'isAutoGenerated': event.is_auto_generated,
                'relatedUserId': event.related_user.id if event.related_user else None,
                'visibility_type': event.visibility_type,
                'visible_to_classes': visible_classes,
                'visible_to_students': visible_students
            }
            return JsonResponse(data)
        elif request.method == 'PUT':
            data = json.loads(request.body)
            if event.is_auto_generated:
                return JsonResponse({'error': 'Cannot edit auto-generated events'}, status=403)
            event.title = data.get('title', event.title)
            event.description = data.get('description', event.description)
            event.all_day = data.get('allDay', event.all_day)
            if 'start' in data:
                event.start_time = datetime.fromisoformat(data['start'].replace('Z', '+00:00'))
            if 'end' in data and data['end']:
                event.end_time = datetime.fromisoformat(data['end'].replace('Z', '+00:00'))
            else:
                event.end_time = None
            event.background_color = data.get('backgroundColor', event.background_color)
            event.repeats = data.get('repeats', event.repeats)
            if 'repeatUntil' in data and data['repeatUntil']:
                event.repeat_until = datetime.fromisoformat(data['repeatUntil'].replace('Z', '+00:00')).date()
            else:
                event.repeat_until = None
            if 'visibility_type' in data:
                event.visibility_type = data['visibility_type']
            event.save()
            if 'visible_to_classes' in data and event.visibility_type == 'classes':
                event.visible_to_classes.set(data['visible_to_classes'])
            if 'visible_to_students' in data and event.visibility_type == 'students':
                event.visible_to_students.set(data['visible_to_students'])
            return JsonResponse({'status': 'success', 'id': event.id})
        elif request.method == 'DELETE':
            if event.is_auto_generated and event.is_birthday:
                event.delete()
                return JsonResponse({'status': 'success', 'message': 'Birthday event removed'})
            elif event.is_auto_generated:
                return JsonResponse({'error': 'Cannot delete auto-generated events'}, status=403)
            event.delete()
            return JsonResponse({'status': 'success'})
    except CalendarEvent.DoesNotExist:
        return JsonResponse({'error': 'Event not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def create_calendar_event(request):
    """api to create calendar event"""
    if not (request.user.is_staff or request.user.is_teacher):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            event = CalendarEvent(
                title=data['title'],
                description=data.get('description', ''),
                all_day=data.get('allDay', False),
                background_color=data.get('backgroundColor', '#3c8dbc'),
                created_by=request.user,
                repeats=data.get('repeats', False),
                visibility_type=data.get('visibility_type', 'all')
            )
            event.start_time = datetime.fromisoformat(data['start'].replace('Z', '+00:00'))
            if 'end' in data and data['end']:
                event.end_time = datetime.fromisoformat(data['end'].replace('Z', '+00:00'))
            if event.repeats and 'repeatUntil' in data and data['repeatUntil']:
                event.repeat_until = datetime.fromisoformat(
                    data['repeatUntil'].replace('Z', '+00:00')
                ).date()
            event.save()
            if event.visibility_type == 'classes' and 'visible_to_classes' in data:
                class_ids = data['visible_to_classes']
                event.visible_to_classes.set(class_ids)
            elif event.visibility_type == 'students' and 'visible_to_students' in data:
                student_ids = data['visible_to_students']
                event.visible_to_students.set(student_ids)
            return JsonResponse({
                'status': 'success',
                'id': event.id,
                'title': event.title
            })
        except KeyError as e:
            return JsonResponse({'error': f'Missing required field: {str(e)}'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
def generate_birthday_events(request):
    """generate birthday events"""
    if not (request.user.is_staff or request.user.is_teacher):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    if request.method == 'POST':
        try:
            CalendarEvent.generate_birthday_events()
            count = CalendarEvent.objects.filter(is_birthday=True, is_auto_generated=True).count()
            return JsonResponse({
                'status': 'success',
                'message': f'Successfully generated {count} birthday events'
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
def delete_birthday_events(request):
    """delete birthday events"""
    if not (request.user.is_staff or request.user.is_teacher):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    if request.method == 'DELETE':
        try:
            count = CalendarEvent.objects.filter(is_birthday=True, is_auto_generated=True).delete()[0]
            return JsonResponse({
                'status': 'success',
                'message': f'Successfully deleted {count} birthday events'
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
def toggle_birthday_events(request):
    """toggle birthday events"""
    if not (request.user.is_staff or request.user.is_teacher):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    if request.method == 'POST':
        try:
            current_state = cache.get('birthday_events_enabled', True)
            new_state = not current_state
            cache.set('birthday_events_enabled', new_state, None)
            if new_state:
                count = CalendarEvent.generate_birthday_events()
                return JsonResponse({
                    'status': 'success',
                    'enabled': True,
                    'message': f'Birthday events enabled. Generated {count} events.'
                })
            else:
                count = CalendarEvent.objects.filter(is_birthday=True).delete()[0]
                return JsonResponse({
                    'status': 'success',
                    'enabled': False,
                    'message': f'Birthday events disabled. Removed {count} events.'
                })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
def delete_all_calendar_events(request):
    """delete all calendar events"""
    if not (request.user.is_staff or request.user.is_teacher):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    if request.method == 'DELETE':
        try:
            data = json.loads(request.body) if request.body else {}
            keep_auto_generated = data.get('keep_auto_generated', True)
            if keep_auto_generated:
                count = CalendarEvent.objects.filter(is_auto_generated=False).delete()[0]
                message = f"Successfully deleted {count} manually created events"
            else:
                count = CalendarEvent.objects.all().delete()[0]
                message = f"Successfully deleted all {count} events"
            return JsonResponse({
                'status': 'success',
                'message': message
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
def get_classes_and_students(request):
    """api to get classes and students"""
    if not (request.user.is_staff or request.user.is_teacher):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    classes = Unit.objects.all()
    classes_data = [{'id': unit.id, 'name': unit.name} for unit in classes]
    students = CustomUser.objects.filter(is_student=True)
    students_data = [{'id': student.id, 'name': student.get_full_name() or student.username} for student in students]
    return JsonResponse({
        'classes': classes_data,
        'students': students_data
    })

@login_required
def users_list(request):
    """list of users"""
    if not (request.user.is_staff or request.user.is_teacher):
        messages.error(request, "Permission denied")
        return redirect('dashboardv1')
    sort_by = request.GET.get('sort_by', 'username')
    filter_gender = request.GET.get('gender', '')
    filter_role = request.GET.get('role', '')
    filter_belt = request.GET.get('belt', '')
    search_query = request.GET.get('q', '')
    users = CustomUser.objects.all()
    if search_query:
        users = users.filter(
            models.Q(username__icontains=search_query) |
            models.Q(first_name__icontains=search_query) |
            models.Q(last_name__icontains=search_query) |
            models.Q(email__icontains=search_query)
        )
    if filter_gender:
        users = users.filter(gender=filter_gender)
    if filter_belt:
        users = users.filter(belt=filter_belt)
    if filter_role == 'student':
        users = users.filter(is_student=True)
    elif filter_role == 'teacher':
        users = users.filter(is_teacher=True)
    elif filter_role == 'admin':
        users = users.filter(is_staff=True, is_teacher=False, is_student=False)
    users = users.order_by(sort_by)
    students = users.filter(is_student=True)
    teachers = users.filter(is_teacher=True)
    admins = users.filter(is_staff=True, is_teacher=False, is_student=False)
    context = {
        'students': students,
        'teachers': teachers,
        'admins': admins,
        'sort_by': sort_by,
        'filter_gender': filter_gender,
        'filter_role': filter_role,
        'filter_belt': filter_belt,
        'search_query': search_query,
        'belt_choices': CustomUser.BELT_CHOICES,
        'gender_choices': [("female", "Female"), ("male", "Male"), ("other", "Other")],
        'title': 'Users Management',
        'parent': 'users',
        'segment': 'users_list',
    }
    return render(request, 'pages/instructor/users.html', context)

@login_required
def user_info(request, user_id):
    """view user info"""
    if not (request.user.is_staff or request.user.is_teacher):
        messages.error(request, "Permission denied")
        return redirect('dashboardv1')
    user = get_object_or_404(CustomUser, id=user_id)
    if request.user.is_teacher and not request.user.is_staff and not user.is_student:
        messages.error(request, "Teachers can only edit student information")
        return redirect('users_list')
    if request.method == 'POST':
        user.username = request.POST.get('username', user.username)
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.gender = request.POST.get('gender', user.gender)
        dob_str = request.POST.get('dob')
        if dob_str:
            try:
                user.dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, "Invalid date format for date of birth")
        user.address = request.POST.get('address', user.address)
        user.province = request.POST.get('province', user.province)
        user.city = request.POST.get('city', user.city)
        if request.user.is_staff:
            belt = request.POST.get('belt')
            if belt in dict(CustomUser.BELT_CHOICES):
                user.belt = belt
        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']
        new_password = request.POST.get('new_password')
        if new_password:
            confirm_password = request.POST.get('confirm_password')
            if new_password == confirm_password:
                user.set_password(new_password)
                messages.success(request, "Password changed successfully")
            else:
                messages.error(request, "Passwords do not match")
        user.save()
        messages.success(request, f"User {user.username} updated successfully")
        return redirect('user_info', user_id=user.id)
    context = {
        'user_data': user,
        'belt_choices': CustomUser.BELT_CHOICES,
        'gender_choices': [("female", "Female"), ("male", "Male"), ("other", "Other")],
        'title': f'User Info: {user.get_full_name() or user.username}',
        'parent': 'users',
        'segment': 'user_info',
        'now': timezone.now(),
    }
    return render(request, 'pages/instructor/user_info.html', context)

@login_required
def create_user(request, dojo_id=None):
    """create new user"""
    if not (request.user.is_staff or request.user.is_teacher):
        messages.error(request, "Permission denied")
        return redirect('dashboardv1')
    user_type = request.GET.get('type', 'student')
    selected_dojo = None
    if dojo_id:
        try:
            selected_dojo = Dojo.objects.get(id=dojo_id)
        except Dojo.DoesNotExist:
            messages.error(request, "The specified dojo was not found.")
            return redirect('dojo_list')
    dojos = None
    if request.user.is_superuser and not selected_dojo:
        dojos = Dojo.objects.all().order_by('name')
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        address = request.POST.get('address')
        city = request.POST.get('city')
        province = request.POST.get('province')
        belt = request.POST.get('belt')
        gender = request.POST.get('gender')
        dob = request.POST.get('dob')
        user_type = request.POST.get('user_type')
        form_dojo_id = request.POST.get('dojo_id')
        user_dojo = None
        if form_dojo_id:
            try:
                user_dojo = Dojo.objects.get(id=form_dojo_id)
            except Dojo.DoesNotExist:
                messages.error(request, "Selected dojo not found")
                return redirect('create_user')
        elif selected_dojo:
            user_dojo = selected_dojo
        elif not request.user.is_superuser and request.user.dojo:
            user_dojo = request.user.dojo
        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect('create_user')
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('create_user')
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already exists")
            return redirect('create_user')
        try:
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            user.address = address
            user.city = city
            user.province = province
            user.belt = belt
            user.gender = gender
            user.dojo = user_dojo
            if dob:
                try:
                    user.dob = datetime.strptime(dob, '%Y-%m-%d').date()
                except ValueError:
                    pass
            if user_type == 'teacher':
                user.is_teacher = True
                user.is_staff = True
            else:
                user.is_student = True
            if 'profile_picture' in request.FILES:
                user.profile_picture = request.FILES['profile_picture']
            user.save()
            user_role = "Instructor" if user_type == 'teacher' else "Student"
            dojo_name = user_dojo.name if user_dojo else "No Dojo"
            messages.success(request, f"{user_role} {username} created successfully for {dojo_name}")
            if selected_dojo:
                return redirect('dojo_detail', dojo_id=selected_dojo.id)
            else:
                return redirect('users_list')
        except Exception as e:
            messages.error(request, f"Error creating user: {str(e)}")
            return redirect('create_user')
    context = {
        'user_type': user_type,
        'title': 'Create New User',
        'parent': 'users',
        'segment': 'create_user',
        'selected_dojo': selected_dojo,
        'dojos': dojos,
        'dojo_id': dojo_id if dojo_id else None,
    }
    return render(request, 'pages/instructor/create_user.html', context)

@login_required
def edit_class(request, unit_id=None):
    """create or edit class"""
    if not (request.user.is_staff or request.user.is_teacher):
        messages.error(request, "Permission denied")
        return redirect('dashboardv1')
    selected_dojo_id = request.session.get('selected_dojo_id')
    if not selected_dojo_id and not request.user.dojo:
        messages.warning(request, "Please select a dojo first")
        return redirect('select_dojo')
    dojo_id = selected_dojo_id if selected_dojo_id else request.user.dojo.id
    try:
        dojo = Dojo.objects.get(id=dojo_id)
    except Dojo.DoesNotExist:
        messages.error(request, "Selected dojo not found")
        return redirect('select_dojo')
    unit = None
    registrations = []
    if unit_id:
        unit = get_object_or_404(Unit, id=unit_id)
        if unit.dojo.id != dojo.id:
            messages.error(request, "This class does not belong to the selected dojo")
            return redirect('dashboardv1')
        registrations = Registration.objects.filter(unit=unit).select_related('student')
    teachers = CustomUser.objects.filter(is_teacher=True, dojo=dojo).order_by('first_name', 'last_name')
    if unit:
        registered_student_ids = Registration.objects.filter(unit=unit).values_list('student_id', flat=True)
        available_students = CustomUser.objects.filter(
            is_student=True, 
            dojo=dojo
        ).exclude(id__in=registered_student_ids).order_by('first_name', 'last_name')
    else:
        available_students = CustomUser.objects.filter(
            is_student=True, 
            dojo=dojo
        ).order_by('first_name', 'last_name')
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        teacher_id = request.POST.get('teacher')
        if not name or not code:
            messages.error(request, "Name and code are required")
        else:
            teacher = None
            if teacher_id:
                try:
                    teacher = CustomUser.objects.get(id=teacher_id, is_teacher=True)
                except CustomUser.DoesNotExist:
                    messages.warning(request, "Selected teacher not found")
            if unit:
                unit.name = name
                unit.code = code
                unit.teacher = teacher
                unit.dojo = dojo
            else:
                unit = Unit(
                    name=name,
                    code=code,
                    teacher=teacher,
                    dojo=dojo
                )
            try:
                unit.save()
                messages.success(request, f"Class '{name}' has been {'updated' if unit_id else 'created'} successfully")
                return redirect('admin_student_list', unit_id=unit.id)
            except Exception as e:
                messages.error(request, f"Error saving class: {str(e)}")
    context = {
        'unit': unit,
        'registrations': registrations,
        'teachers': teachers,
        'available_students': available_students,
        'selected_dojo': dojo,
        'title': 'Edit Class' if unit else 'Create Class',
        'parent': 'classes',
        'segment': 'edit_class',
    }
    return render(request, 'pages/instructor/edit_class.html', context)

@login_required
def delete_class(request, unit_id):
    if not (request.user.is_staff or request.user.is_teacher):
        messages.error(request, "Permission denied")
        return redirect('dashboardv1')
    unit = get_object_or_404(Unit, id=unit_id)
    unit_name = unit.name
    unit.delete()
    messages.success(request, f"Class '{unit_name}' has been deleted.")
    return redirect('admin:index')

@login_required
def add_students_to_class(request):
    """add students to class"""
    if not (request.user.is_staff or request.user.is_teacher):
        messages.error(request, "Permission denied")
        return redirect('dashboardv1')
    if request.method == 'POST':
        unit_id = request.POST.get('unit_id')
        student_ids = request.POST.getlist('student_ids')
        if not unit_id or not student_ids:
            messages.error(request, "Missing required information")
            return redirect('admin:index')
        unit = get_object_or_404(Unit, id=unit_id)
        active_session = Session.objects.filter(is_active=True).first()
        if not active_session:
            current_year = timezone.now().year
            active_session = Session.objects.create(
                name=f"Session {current_year}",
                start_date=timezone.now().date(),
                end_date=timezone.now().date() + timezone.timedelta(days=180),
                academic_year=f"{current_year}-{current_year+1}",
                is_active=True,
                dojo=unit.dojo
            )
        count = 0
        for student_id in student_ids:
            try:
                student = CustomUser.objects.get(id=student_id, is_student=True)
                if not Registration.objects.filter(student=student, unit=unit).exists():
                    Registration.objects.create(
                        student=student,
                        unit=unit,
                        session=active_session
                    )
                    count += 1
            except CustomUser.DoesNotExist:
                continue
        messages.success(request, f"Added {count} student(s) to {unit.name}")
        return redirect('edit_class', unit_id=unit_id)
    return redirect('admin:index')

@login_required
def remove_student_from_class(request):
    """remove student from class"""
    if not (request.user.is_staff or request.user.is_teacher):
        messages.error(request, "Permission denied")
        return redirect('dashboardv1')
    if request.method == 'POST':
        registration_id = request.POST.get('registration_id')
        unit_id = request.POST.get('unit_id')
        if not registration_id or not unit_id:
            messages.error(request, "Missing required information")
            return redirect('admin:index')
        try:
            registration = Registration.objects.get(id=registration_id)
            student_name = registration.student.get_full_name() or registration.student.username
            registration.delete()
            messages.success(request, f"Removed {student_name} from class")
        except Registration.DoesNotExist:
            messages.error(request, "Student registration not found")
        return redirect('edit_class', unit_id=unit_id)
    return redirect('admin:index')

@login_required
def delete_user(request, user_id):
    """delete user"""
    if not (request.user.is_staff or request.user.is_teacher):
        messages.error(request, "Permission denied")
        return redirect('dashboardv1')
    user_to_delete = get_object_or_404(CustomUser, id=user_id)
    if request.user.is_teacher and not request.user.is_staff:
        if not user_to_delete.is_student:
            messages.error(request, "Teachers can only delete students")
            return redirect('users_list')
    if user_to_delete.id == request.user.id:
        messages.error(request, "You cannot delete your own account")
        return redirect('users_list')
    user_name = user_to_delete.get_full_name() or user_to_delete.username
    user_role = "Administrator" if user_to_delete.is_staff else ("Instructor" if user_to_delete.is_teacher else "Student")
    try:
        user_to_delete.delete()
        messages.success(request, f"{user_role} {user_name} has been deleted successfully")
    except Exception as e:
        messages.error(request, f"Error deleting user: {str(e)}")
    return redirect('users_list')

def register_with_dojo_code(request, code):
    """register with dojo code"""
    try:
        reg_link = DojoRegistrationLink.objects.get(code=code)
        if not reg_link.is_valid():
            messages.error(request, "This registration link has expired or is no longer active.")
            return redirect('login')
        if reg_link.max_uses > 0 and reg_link.uses_count >= reg_link.max_uses:
            messages.error(request, "This registration link has reached its maximum usage limit.")
            return redirect('login')
        request.session['registration_dojo_id'] = reg_link.dojo.id
        request.session['registration_code'] = code
        messages.success(request, f"You're registering with {reg_link.dojo.name}. Please complete your information.")
        return redirect('register_student')
    except DojoRegistrationLink.DoesNotExist:
        messages.error(request, "Invalid registration link.")
        return redirect('login')

@login_required
def dojo_list(request):
    """view all dojos"""
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.is_superuser:
        dojos = Dojo.objects.all().order_by('name')
    elif request.user.dojo:
        dojos = Dojo.objects.filter(id=request.user.dojo.id)
    else:
        dojos = Dojo.objects.none()
    if request.method == 'POST' and request.user.is_superuser:
        name = request.POST.get('name')
        if name:
            dojo = Dojo(
                name=name,
                address=request.POST.get('address', ''),
                city=request.POST.get('city', ''),
                province=request.POST.get('province', ''),
                country=request.POST.get('province', ''),
                phone=request.POST.get('phone', ''),
                email=request.POST.get('email', ''),
            )
            if 'logo' in request.FILES:
                dojo.logo = request.FILES['logo']
            dojo.save()
            messages.success(request, f"Dojo '{name}' created successfully!")
            return redirect('dojo_detail', dojo_id=dojo.id)
        else:
            messages.error(request, "Dojo name is required.")
    context = {
        'dojos': dojos,
        'can_create': request.user.is_superuser,
        'title': 'Dojos',
        'parent': 'dojos',
        'segment': 'dojo_list',
    }
    return render(request, 'pages/instructor/dojo_list.html', context)

@login_required
def dojo_detail(request, dojo_id):
    """view dojo details"""
    dojo = get_object_or_404(Dojo, id=dojo_id)
    if not (request.user.is_superuser or (request.user.dojo and request.user.dojo.id == dojo_id)):
        messages.error(request, "You don't have permission to view this dojo.")
        return redirect('dashboardv1')
    if request.method == 'POST' and request.user.is_superuser:
        dojo.name = request.POST.get('name', dojo.name)
        dojo.address = request.POST.get('address', dojo.address)
        dojo.city = request.POST.get('city', dojo.city)
        dojo.province = request.POST.get('province', dojo.province)
        dojo.country = request.POST.get('country', dojo.country)
        dojo.phone = request.POST.get('phone', dojo.phone)
        dojo.email = request.POST.get('email', dojo.email)
        dojo.website = request.POST.get('website', dojo.website)
        if 'logo' in request.FILES:
            dojo.logo = request.FILES['logo']
        dojo.save()
        messages.success(request, f"Dojo '{dojo.name}' updated successfully!")
    data_type = request.GET.get('data')
    if data_type:
        if data_type == 'students':
            students = CustomUser.objects.filter(dojo=dojo, is_student=True)
            return render(request, 'pages/instructor/_student_list_partial.html', {'students': students})
        elif data_type == 'instructors':
            instructors = CustomUser.objects.filter(dojo=dojo, is_teacher=True)
            return render(request, 'pages/instructor/_instructor_list_partial.html', {'instructors': instructors})
    student_count = dojo.get_student_count()
    instructor_count = dojo.get_instructor_count()
    units = Unit.objects.filter(dojo=dojo).select_related('teacher')
    reg_links = DojoRegistrationLink.objects.filter(dojo=dojo, is_active=True)
    context = {
        'dojo': dojo,
        'units': units,
        'student_count': student_count,
        'instructor_count': instructor_count,
        'registration_links': reg_links,
        'can_edit': request.user.is_superuser,
        'title': f'Dojo: {dojo.name}',
        'parent': 'dojos',
        'segment': 'dojo_detail',
    }
    return render(request, 'pages/instructor/dojo_detail.html', context)

@login_required
def create_registration_link(request, dojo_id):
    """create registration link for dojo"""
    dojo = get_object_or_404(Dojo, id=dojo_id)
    if not request.user.is_staff and (not request.user.dojo or request.user.dojo.id != dojo_id):
        messages.error(request, "You don't have permission to create registration links for this dojo.")
        return redirect('dojo_list')
    if request.method == 'POST':
        description = request.POST.get('description')
        expires_days = request.POST.get('expires_days', 0)
        max_uses = request.POST.get('max_uses', 0)
        try:
            code = DojoRegistrationLink.generate_code()
            while DojoRegistrationLink.objects.filter(code=code).exists():
                code = DojoRegistrationLink.generate_code()
            expires_at = None
            if int(expires_days) > 0:
                expires_at = timezone.now() + timedelta(days=int(expires_days))
            reg_link = DojoRegistrationLink.objects.create(
                dojo=dojo,
                code=code,
                description=description,
                max_uses=int(max_uses),
                expiration_date=expires_at,
                created_by=request.user
            )
            messages.success(request, f"Registration link created successfully! Code: {code}")
            return redirect('dojo_detail', dojo_id=dojo.id)
        except Exception as e:
            messages.error(request, f"Error creating registration link: {str(e)}")
            return redirect('create_registration_link', dojo_id=dojo.id)
    context = {
        'dojo': dojo,
        'title': f'Create Registration Link for {dojo.name}',
        'parent': 'dojos',
        'segment': 'create_registration_link',
    }
    return render(request, 'pages/instructor/create_registration_link.html', context)

@login_required
def manage_registration_links(request):
    """manage registration links"""
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.is_superuser:
        dojos = Dojo.objects.all()
    elif request.user.is_staff or request.user.is_teacher:
        if request.user.dojo:
            dojos = Dojo.objects.filter(id=request.user.dojo.id)
        else:
            dojos = Dojo.objects.none()
    else:
        messages.error(request, "You don't have permission to manage registration links.")
        return redirect('dashboardv1')
    registration_links = DojoRegistrationLink.objects.filter(
        dojo__in=dojos
    ).select_related('dojo', 'created_by').order_by('-created_at')
    if request.method == 'POST':
        link_id = request.POST.get('link_id')
        action = request.POST.get('action')
        if link_id and action:
            try:
                reg_link = DojoRegistrationLink.objects.get(id=link_id)
                if not request.user.is_superuser and (not request.user.dojo or request.user.dojo.id != reg_link.dojo.id):
                    messages.error(request, "You don't have permission to modify this registration link.")
                else:
                    if action == 'activate':
                        reg_link.is_active = True
                        reg_link.save()
                        messages.success(request, "Registration link activated.")
                    elif action == 'deactivate':
                        reg_link.is_active = False
                        reg_link.save()
                        messages.success(request, "Registration link deactivated.")
                    elif action == 'delete':
                        reg_link.delete()
                        messages.success(request, "Registration link deleted.")
            except DojoRegistrationLink.DoesNotExist:
                messages.error(request, "Registration link not found.")
        else:
            messages.error(request, "Invalid request.")
    context = {
        'registration_links': registration_links,
        'title': 'Manage Registration Links',
        'parent': 'dojos',
        'segment': 'manage_registration_links',
    }
    return render(request, 'pages/instructor/manage_registration_links.html', context)

@login_required
def create_dojo(request):
    """create new dojo"""
    if not request.user.is_superuser:
        messages.error(request, "Only administrators can create new dojos.")
        return redirect('dojo_list')
    if request.method == 'POST':
        name = request.POST.get('name')
        if not name:
            messages.error(request, "Dojo name is required.")
            return render(request, 'pages/instructor/create_dojo.html')
        dojo = Dojo(
            name=name,
            address=request.POST.get('address', ''),
            phone=request.POST.get('phone', ''),
            email=request.POST.get('email', ''),
            description=request.POST.get('description', '')
        )
        dojo.save()
        messages.success(request, f"Dojo '{name}' created successfully!")
        return redirect('dojo_detail', dojo_id=dojo.id)
    context = {
        'title': 'Create New Dojo',
        'parent': 'dojos',
        'segment': 'create_dojo',
    }
    return render(request, 'pages/instructor/create_dojo.html', context)

@login_required
def select_dojo(request):
    """select dojo to manage"""
    if not (request.user.is_staff or request.user.is_teacher):
        messages.error(request, "Permission denied")
        return redirect('dashboardv1')
    if request.user.is_superuser:
        dojos = Dojo.objects.all().order_by('name')
    elif request.user.is_teacher or request.user.is_staff:
        if request.user.dojo:
            dojos = Dojo.objects.filter(id=request.user.dojo.id)
        else:
            messages.warning(request, "You don't have access to any dojos. Please contact an administrator.")
            return redirect('dashboardv1')
    else:
        dojos = Dojo.objects.none()
    if request.method == 'POST':
        dojo_id = request.POST.get('dojo_id')
        try:
            selected_dojo = Dojo.objects.get(id=dojo_id)
            request.session['selected_dojo_id'] = selected_dojo.id
            request.session['selected_dojo_name'] = selected_dojo.name
            messages.success(request, f"Now managing {selected_dojo.name}")
            return redirect('dashboardv1')
        except Dojo.DoesNotExist:
            messages.error(request, "Invalid dojo selection")
    selected_dojo_id = request.session.get('selected_dojo_id')
    context = {
        'dojos': dojos,
        'selected_dojo_id': selected_dojo_id,
        'title': 'Select Dojo to Manage',
        'parent': 'dojos',
        'segment': 'select_dojo',
    }
    return render(request, 'pages/instructor/select_dojo.html', context)