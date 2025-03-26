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


# User Registration View
def register(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        # Validation checks
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('register')
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('register')
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect('register')
        
        # Create user using CustomUser model
        user = CustomUser.objects.create_user(username=username, email=email, password=password)
        user.save()
        messages.success(request, "Registration successful. Please log in.")
        return redirect('login')
    
    return render(request, 'auth/register.html')


def login_redirect_view(request):
    return redirect('/')
def user_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        print(f"Attempting login with username: {username}")

        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            print(f"User {username} logged in successfully.")
            
            if user.is_student:
                return redirect('student_dashboard')
            elif user.is_teacher:
                return redirect('teacher_dashboard')
            else:
                messages.error(request, "Invalid user role.")
                return redirect('login')
        else:
            print(f"Failed login attempt for username: {username}")
            return render(request, "auth/login.html", {"error_message": "Invalid username or password"})
    
    return render(request, 'auth/login.html')

@login_required
def user_logout(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('login')

@login_required
def register_units(request):
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


def register_student(request):
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_student = True 
            user.save()
            return redirect('login')  
    else:
        form = StudentRegistrationForm()
    return render(request, 'auth/register_student.html', {'form': form})

def register_teacher(request):
    if request.method == 'POST':
        form = TeacherRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_teacher = True  # Assign role as teacher
            user.save()
            return redirect('login')  # Redirect to login page after successful registration
    else:
        form = TeacherRegistrationForm()
    return render(request, 'auth/register_teacher.html', {'form': form})



@login_required
def submit_assignment(request, event_id):
    if not request.user.is_student:
        return redirect('login')
        
    assignment_event = get_object_or_404(
        TimelineEvent, 
        id=event_id, 
        student=request.user, 
        event_type='assignment'
    )
    
    if request.method == 'POST':
        # Update the assignment event (if needed)
        assignment_event.is_submitted = True
        assignment_event.submission_notes = request.POST.get('notes', '')
        assignment_event.submission_date = timezone.now()
        
        if 'submission_file' in request.FILES:
            # Save the file on the assignment event if you want to keep a copy there
            assignment_event.submission_file = request.FILES['submission_file']
        assignment_event.save()
        
        # Create a Submission object linked to the assignment event
        Submission.objects.create(
            assignment=assignment_event,
            student=request.user,
            file=request.FILES.get('submission_file'),  # May be None if no file uploaded.
            notes=request.POST.get('notes', '')
        )
        
        messages.success(request, 'Assignment submitted successfully!')
        return redirect('assignments')
        
    return redirect('assignments')

@login_required
def students_in_unit(request, unit_id):
    if not request.user.is_teacher:
        return redirect('login')
    unit = Unit.objects.get(id=unit_id)
    registrations = Registration.objects.filter(unit=unit)
    return render(request, 'portal/students_in_unit.html', {'unit': unit, 'registrations': registrations})


@login_required
def view_submissions(request, assignment_id):
    if not request.user.is_teacher:
        return redirect('login')
    assignment = Assignment.objects.get(id=assignment_id)
    submissions = Submission.objects.filter(assignment=assignment)
    return render(request, 'portal/view_submissions.html', {'assignment': assignment, 'submissions': submissions})


@login_required
def report_session(request):
    if not request.user.is_student:
        return redirect('login')
    # Logic for reporting the session
    # Example: Just a confirmation page
    if request.method == 'POST':
        # Handle session reporting logic
        return redirect('student_dashboard')
    return render(request, 'portal/report_session.html')

# Student Dashboard
@login_required
def student_dashboard(request):
    if not request.user.is_student:
        return redirect('login')
    
    # Get active assignments
    active_assignments = TimelineEvent.objects.filter(
        student=request.user,
        event_type='assignment',
        is_submitted=False
    ).order_by('due_date')

    # Get counts for statistics
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
    
    # Add notifications to context
    context['notifications'] = request.user.notifications.filter(is_read=False)
    
    return render(request, 'pages/index.html', context)


# Student progress
@login_required
def student_progress(request):
    if not request.user.is_student:
        return redirect('login')
    return render(request, 'pages/student_progress.html')

# student assignments
@login_required
def view_assignment(request):
    if not request.user.is_student:
        return redirect('login')
    
    # Get assignments data
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
    
    # Get all timeline events for the timeline view
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
    if not request.user.is_student:
        return redirect('login')
    
    # Get all timeline events filtered by assessment type
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


# Progress Report

@login_required
def progress_report(request):
    if not request.user.is_student:
        return redirect('login')
    
    return render(request, 'pages/progress.html')


# Teacher Dashboard
@login_required
def teacher_dashboard(request):
    if not request.user.is_teacher:
        return redirect('login')
    units = Unit.objects.filter(teacher=request.user)
    return render(request, 'portal/teacher_dashboard.html', {'units': units})

# Post Assignment
@login_required
def post_assignment(request):
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
    print(f"Number of units: {units.count()}")  # Debug print
    print(f"Units: {units}") #Debug print to show the units
    return render(request, 'portal/post_assignment.html', {'units': units})


@login_required
def admin_student_list(request, unit_id):
    if not request.user.is_staff:
        return redirect('admin:login')
        
    unit = get_object_or_404(Unit, id=unit_id)
    registrations = Registration.objects.filter(unit=unit).select_related('student')

    context = {
        'unit': unit,
        'registrations': registrations,
        'title': f'Students in {unit.name}',
        # Add AdminLTE specific context
        'parent': 'Students',
        'segment': 'student_list',
        'has_permission': True,
        'is_popup': False,
        'has_view_permission': True
    }
    return render(request, 'pages/student_list.html', context)

@login_required
def admin_student_info(request, student_id):
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

    # Get active assignments count (not submitted and not past due date)
    active_count = TimelineEvent.objects.filter(
        student=student,
        event_type='assignment',
        is_submitted=False,
        due_date__gt=timezone.now()
    ).count()

    # Get completed assignments count
    completed_count = TimelineEvent.objects.filter(
        student=student,
        event_type='assignment',
        is_submitted=True
    ).count()
    
    # Get attendance stats
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
    
    return render(request, 'pages/student_info.html', context)

@login_required
def event_detail_api(request, event_id):
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
    if not (request.user.is_staff or request.user.is_teacher):
        messages.error(request, "Permission denied")
        return redirect('admin_student_info', student_id=student_id)
        
    if request.method == 'POST':
        student = get_object_or_404(CustomUser, id=student_id)
        event_type = request.POST.get('event_type')
        title = request.POST.get('title')
        
        event = TimelineEvent.objects.create(
            student=student,
            event_type=event_type,
            title=title,
            content=request.POST.get('content'),
            created_by=request.user
        )
        
        # Add due date for assignments
        if event_type == 'assignment':
            due_date = request.POST.get('due_date')
            event.due_date = timezone.make_aware(datetime.strptime(due_date, '%Y-%m-%d %H:%M:%S'))
        
        # Add result for assessments
        if event_type == 'assessment':
            event.assessment_result = request.POST.get('assessment_result')
        
        event.save()
        
        # Create appropriate notification based on event type
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
    event = get_object_or_404(TimelineEvent, id=event_id)
    
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            feedback = EventFeedback.objects.create(
                event=event,
                author=request.user,
                content=content
            )
            
            # Create notification for student
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
        'user': f.author.get_full_name()  # Changed to use author
    } for f in feedback], safe=False)

def register_v1(request):
  if request.method == 'POST':
    form = RegistrationForm(request.POST)
    if form.is_valid():
      form.save()
      print('Account created successfully!')
      return redirect('/accounts/login/')
    else:
      print("Registration failed!")
  else:
    form = RegistrationForm()
  
  context = {'form': form}
  return render(request, 'pages/examples/register.html', context)

def register_v2(request):
  if request.method == 'POST':
    form = RegistrationForm(request.POST)
    if form.is_valid():
      form.save()
      print('Account created successfully!')
      return redirect('/accounts/login/')
    else:
      print("Registration failed!")
  else:
    form = RegistrationForm()
  
  context = {'form': form}
  return render(request, 'pages/examples/register-v2.html', context)

class UserLoginView(auth_views.LoginView):
  template_name = 'accounts/login.html'
  form_class = LoginForm
  success_url = '/'

class UserLoginViewV1(auth_views.LoginView):
  template_name = 'pages/examples/login.html'
  form_class = LoginForm
  success_url = '/'

class UserLoginViewV2(auth_views.LoginView):
  template_name = 'pages/examples/login-v2.html'
  form_class = LoginForm
  success_url = '/'

class UserPasswordResetView(auth_views.PasswordResetView):
  template_name = 'accounts/forgot-password.html'
  form_class = UserPasswordResetForm

class UserPasswordResetViewV1(auth_views.PasswordResetView):
  template_name = 'pages/examples/forgot-password.html'
  form_class = UserPasswordResetForm

class UserPasswordResetViewV2(auth_views.PasswordResetView):
  template_name = 'pages/examples/forgot-password-v2.html'
  form_class = UserPasswordResetForm

class UserPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
  template_name = 'accounts/recover-password.html'
  form_class = UserSetPasswordForm

class UserPasswordChangeView(auth_views.PasswordChangeView):
  template_name = 'accounts/password_change.html'
  form_class = UserPasswordChangeForm

class UserPasswordChangeViewV1(auth_views.PasswordChangeView):
  template_name = 'pages/examples/recover-password.html'
  form_class = UserPasswordChangeForm

class UserPasswordChangeViewV2(auth_views.PasswordChangeView):
  template_name = 'pages/examples/recover-password-v2.html'
  form_class = UserPasswordChangeForm

def user_logout_view(request):
  logout(request)
  return redirect('/accounts/login/')



# pages
def index(request):
  context = {
    'parent': 'dashboard',
    'segment': 'dashboardv1'
  }
  return render(request, 'pages/index.html', context)

def index2(request):
  context = {
    'parent': 'dashboard',
    'segment': 'dashboardv2'
  }
  return render(request, 'pages/index2.html', context)

def index3(request):
  context = {
    'parent': 'dashboard',
    'segment': 'dashboardv3'
  }
  return render(request, 'pages/index3.html', context)

def widgets(request):
  context = {
    'parent': '',
    'segment': 'widgets'
  }
  return render(request, 'pages/widgets.html', context)

# EXAMPLES

def examples_calendar(request):
  context = {
    'parent': '',
    'segment': 'calendar'
  }
  return render(request, 'pages/calendar.html', context)

def examples_gallery(request):
  context = {
    'parent': '',
    'segment': 'gallery'
  }
  return render(request, 'pages/gallery.html', context)

def examples_kanban(request):
  context = {
    'parent': '',
    'segment': 'kanban_board'
  }
  return render(request, 'pages/kanban.html', context)

# Mailbox

def mailbox_inbox(request):
  context = {
    'parent': 'mailbox',
    'segment': 'inbox'
  }
  return render(request, 'pages/mailbox/mailbox.html', context)

def mailbox_compose(request):
  context = {
    'parent': 'mailbox',
    'segment': 'compose'
  }
  return render(request, 'pages/mailbox/compose.html', context)

def mailbox_read_mail(request):
  context = {
    'parent': 'mailbox',
    'segment': 'read_mail'
  }
  return render(request, 'pages/mailbox/read-mail.html', context)

# Pages -- Examples

def examples_invoice(request):
  context = {
    'parent': 'pages',
    'segment': 'invoice'
  }
  return render(request, 'pages/examples/invoice.html', context)

def invoice_print(request):
  context = {
    'parent': 'pages',
    'segment': 'invoice_print'
  }
  return render(request, 'pages/examples/invoice-print.html', context)

def examples_profile(request):
  context = {
    'parent': 'pages',
    'segment': 'profile'
  }
  return render(request, 'pages/examples/profile.html', context)

def examples_e_commerce(request):
  context = {
    'parent': 'pages',
    'segment': 'ecommerce'
  }
  return render(request, 'pages/examples/e-commerce.html', context)

def examples_projects(request):
  context = {
    'parent': 'pages',
    'segment': 'projects'
  }
  return render(request, 'pages/examples/projects.html', context)

def examples_project_add(request):
  context = {
    'parent': 'pages',
    'segment': 'project_add'
  }
  return render(request, 'pages/examples/project-add.html', context)

def examples_project_edit(request):
  context = {
    'parent': 'pages',
    'segment': 'project_edit'
  }
  return render(request, 'pages/examples/project-edit.html', context)

def examples_project_detail(request):
  context = {
    'parent': 'pages',
    'segment': 'project_detail'
  }
  return render(request, 'pages/examples/project-detail.html', context)

def examples_contacts(request):
  context = {
    'parent': 'pages',
    'segment': 'contacts'
  }
  return render(request, 'pages/examples/contacts.html', context)

def examples_faq(request):
  context = {
    'parent': 'pages',
    'segment': 'faq'
  }
  return render(request, 'pages/examples/faq.html', context)

def examples_contact_us(request):
  context = {
    'parent': 'pages',
    'segment': 'contact_us'
  }
  return render(request, 'pages/examples/contact-us.html', context)

# Extra -- login & Registration v1
# def login_v1(request):
#   context = {
#     'parent': '',
#     'segment': ''
#   }
#   return render(request, 'pages/examples/login.html', context)

# def login_v2(request):
#   context = {
#     'parent': '',
#     'segment': ''
#   }
#   return render(request, 'pages/examples/login-v2.html', context)

# def registration_v1(request):
#   context = {
#     'parent': '',
#     'segment': ''
#   }
#   return render(request, 'pages/examples/register.html', context)

# def registration_v2(request):
#   context = {
#     'parent': '',
#     'segment': ''
#   }
#   return render(request, 'pages/examples/register-v2.html', context)

# def forgot_password_v1(request):
#   context = {
#     'parent': '',
#     'segment': ''
#   }
#   return render(request, 'pages/examples/forgot-password.html', context)

# def forgot_password_v2(request):
#   context = {
#     'parent': '',
#     'segment': ''
#   }
#   return render(request, 'pages/examples/forgot-password-v2.html', context)

# def recover_password_v1(request):
#   context = {
#     'parent': '',
#     'segment': ''
#   }
#   return render(request, 'pages/examples/recover-password.html', context)

# def recover_password_v2(request):
#   context = {
#     'parent': '',
#     'segment': ''
#   }
#   return render(request, 'pages/examples/recover-password-v2.html', context)

def lockscreen(request):
  context = {
    'parent': '',
    'segment': ''
  }
  return render(request, 'pages/examples/lockscreen.html', context)

def legacy_user_menu(request):
  context = {
    'parent': 'extra',
    'segment': 'legacy_user'
  }
  return render(request, 'pages/examples/legacy-user-menu.html', context)

def language_menu(request):
  context = {
    'parent': 'extra',
    'segment': 'legacy_menu'
  }
  return render(request, 'pages/examples/language-menu.html', context)

def error_404(request):
  context = {
    'parent': 'extra',
    'segment': 'error_404'
  }
  return render(request, 'pages/examples/404.html', context)

def error_500(request):
  context = {
    'parent': 'extra',
    'segment': 'error_500'
  }
  return render(request, 'pages/examples/500.html', context)

def pace(request):
  context = {
    'parent': 'extra',
    'segment': 'pace'
  }
  return render(request, 'pages/examples/pace.html', context)

def blank_page(request):
  context = {
    'parent': 'extra',
    'segment': 'blank_page'
  }
  return render(request, 'pages/examples/blank.html', context)

def starter_page(request):
  context = {
    'parent': 'extra',
    'segment': 'starter_page'
  }
  return render(request, 'pages/examples/starter.html', context)

# Search

def search_simple(request):
  context = {
    'parent': 'search',
    'segment': 'search_simple'
  }
  return render(request, 'pages/search/simple.html', context)

def search_enhanced(request):
  context = {
    'parent': 'search',
    'segment': 'search_enhanced'
  }
  return render(request, 'pages/search/enhanced.html', context)

def simple_results(request):
  context = {
    'parent': '',
    'segment': ''
  }
  return render(request, 'pages/search/simple-results.html', context)

def enhanced_results(request):
  context = {
    'parent': '',
    'segment': ''
  }
  return render(request, 'pages/search/enhanced-results.html', context)

# MISCELLANEOUS

def iframe(request):
  context = {
    'parent': '',
    'segment': ''
  }
  return render(request, 'pages/search/iframe.html', context)

# Charts

def chartjs(request):
  context = {
    'parent': 'charts',
    'segment': 'chartjs'
  }
  return render(request, 'pages/charts/chartjs.html', context)

def flot(request):
  context = {
    'parent': 'charts',
    'segment': 'flot'
  }
  return render(request, 'pages/charts/flot.html', context)

def inline(request):
  context = {
    'parent': 'charts',
    'segment': 'inline'
  }
  return render(request, 'pages/charts/inline.html', context)

def uplot(request):
  context = {
    'parent': 'charts',
    'segment': 'uplot'
  }
  return render(request, 'pages/charts/uplot.html', context)

def profile(request):
  context = {
    'parent': 'pages',
    'segment': 'profile'
  }
  return render(request, 'pages/examples/profile.html', context)

# Layout
def top_navigation(request):
  context = {
    'parent': 'layout',
    'segment': 'top_navigation'
  }
  return render(request, 'pages/layout/top-nav.html', context)

def top_nav_sidebar(request):
  context = {
    'parent': 'layout',
    'segment': 'top navigation with sidebar'
  }
  return render(request, 'pages/layout/top-nav-sidebar.html', context)

def boxed(request):
  context = {
    'parent': 'layout',
    'segment': 'boxed_layout'
  }
  return render(request, 'pages/layout/boxed.html', context)

def fixed_sidebar(request):
  context = {
    'parent': 'layout',
    'segment': 'fixed_layout'
  }
  return render(request, 'pages/layout/fixed-sidebar.html', context)

def fixed_sidebar_custom(request):
  context = {
    'parent': 'layout',
    'segment': 'layout_cuastom'
  }
  return render(request, 'pages/layout/fixed-sidebar-custom.html', context)

def fixed_topnav(request):
  context = {
    'parent': 'layout',
    'segment': 'fixed_topNav'
  }
  return render(request, 'pages/layout/fixed-topnav.html', context)

def fixed_footer(request):
  context = {
    'parent': 'layout',
    'segment': 'fixed_footer'
  }
  return render(request, 'pages/layout/fixed-footer.html', context)

def collapsed_sidebar(request):
  context = {
    'parent': 'layout',
    'segment': 'collapsed_sidebar'
  }
  return render(request, 'pages/layout/collapsed-sidebar.html', context)

# UI Elements

def ui_general(request):
  context = {
    'parent': 'ui',
    'segment': 'general'
  }
  return render(request, 'pages/UI/general.html', context)

def ui_icons(request):
  context = {
    'parent': 'ui',
    'segment': 'icons'
  }
  return render(request, 'pages/UI/icons.html', context)

def ui_buttons(request):
  context = {
    'parent': 'ui',
    'segment': 'buttons'
  }
  return render(request, 'pages/UI/buttons.html', context)

def ui_sliders(request):
  context = {
    'parent': 'ui',
    'segment': 'sliders'
  }
  return render(request, 'pages/UI/sliders.html', context)

def ui_modals_alerts(request):
  context = {
    'parent': 'ui',
    'segment': 'modals_alerts'
  }
  return render(request, 'pages/UI/modals.html', context)

def ui_navbar_tabs(request):
  context = {
    'parent': 'ui',
    'segment': 'navbar_tabs'
  }
  return render(request, 'pages/UI/navbar.html', context)

def ui_timeline(request):
  context = {
    'parent': 'ui',
    'segment': 'timeline'
  }
  return render(request, 'pages/UI/timeline.html', context)

def ui_ribbons(request):
  context = {
    'parent': 'ui',
    'segment': 'ribbons'
  }
  return render(request, 'pages/UI/ribbons.html', context)

# Forms

def form_general(request):
  context = {
    'parent': 'forms',
    'segment': 'form_general'
  }
  return render(request, 'pages/forms/general.html', context)

def form_advanced(request):
  context = {
    'parent': 'forms',
    'segment': 'advanced_form'
  }
  return render(request, 'pages/forms/advanced.html', context)

def form_editors(request):
  context = {
    'parent': 'forms',
    'segment': 'text_editors'
  }
  return render(request, 'pages/forms/editors.html', context)

def form_validation(request):
  context = {
    'parent': 'forms',
    'segment': 'validation'
  }
  return render(request, 'pages/forms/validation.html', context)

# Table

def table_simple(request):
  context = {
    'parent': 'tables',
    'segment': 'simple_table'
  }
  return render(request, 'pages/tables/simple.html', context)

def table_data(request):
  context = {
    'parent': 'tables',
    'segment': 'data_table'
  }
  return render(request, 'pages/tables/data.html', context)

def table_jsgrid(request):
  context = {
    'parent': 'tables',
    'segment': 'jsGrid'
  }
  return render(request, 'pages/tables/jsgrid.html', context)

@login_required
def dismiss_notification(request, notification_id):
    if request.method == 'POST':
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def take_attendance(request, unit_id):
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
    
    return render(request, 'pages/take_attendance.html', context)

@login_required
def save_attendance(request):
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
                        event_type='join',  # Using 'join' type for attendance
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
    """Main attendance dashboard listing all units and recent attendance records"""
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
    
    return render(request, 'pages/attendance_list.html', context)

@login_required
def attendance_records(request, unit_id):
    """Detailed attendance records for a specific unit"""
    if not (request.user.is_staff or request.user.is_teacher):
        messages.error(request, "Permission denied")
        return redirect('dashboardv1')
        
    unit = get_object_or_404(Unit, id=unit_id)
    
    # Get all dates with attendance records for this unit
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
    
    return render(request, 'pages/attendance_records.html', context)

@login_required
def edit_attendance(request, attendance_id):
    """Edit a specific attendance record"""
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
    
    return render(request, 'pages/edit_attendance.html', context)

@login_required
def manage_feedback_templates(request):
    """View all feedback templates and add new ones"""
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
    
    return render(request, 'pages/manage_feedback_templates.html', context)

@login_required
def edit_feedback_template(request, template_id):
    """Edit an existing feedback template"""
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
    """Delete a feedback template"""
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
    """API to get all feedback templates for the current user"""
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

