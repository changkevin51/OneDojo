from django.contrib.auth.models import AbstractUser, User
from django.db import models
from django.utils import timezone
from django.conf import settings
import datetime
import time
import random
import string
import uuid

# Dojo Model - Define this first so we can reference it in CustomUser
class Dojo(models.Model):
    """
    Represents a physical dojo/school/location in the system
    """
    name = models.CharField(max_length=100)
    address = models.TextField()
    city = models.CharField(max_length=100, null=True, blank=True)
    province = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def get_student_count(self):
        """Return count of students in this dojo"""
        return CustomUser.objects.filter(dojo=self, is_student=True).count()
    
    def get_instructor_count(self):
        """Return count of instructors in this dojo"""
        return CustomUser.objects.filter(dojo=self, is_teacher=True).count()
        
    class Meta:
        ordering = ['name']
        verbose_name = 'Dojo'
        verbose_name_plural = 'Dojos'


class DojoRegistrationLink(models.Model):
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE, related_name='registration_links')
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    expiration_date = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_links')
    max_uses = models.IntegerField(default=0, help_text="Maximum number of registrations (0 = unlimited)")
    
    def __str__(self):
        return f"{self.dojo.name} - {self.code}"
    
    def is_valid(self):
        if not self.is_active:
            return False
        if self.expiration_date and timezone.now() > self.expiration_date:
            return False
        return True
    
    @property
    def uses_count(self):
        """Return the number of users who registered with this link"""
        return CustomUser.objects.filter(registration_link=self).count()
    
    @property
    def expires_at(self):
        """Alias for expiration_date to match admin field name"""
        return self.expiration_date
    
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = str(uuid.uuid4())[:8]
        super().save(*args, **kwargs)


class CustomUser(AbstractUser):
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    
    # Connect user to dojo
    dojo = models.ForeignKey(Dojo, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    is_student = models.BooleanField(default=False)  # To identify students
    is_teacher = models.BooleanField(default=False)  # To identify teachers

    gender = models.CharField(max_length=10, choices=[("female", "Female"), ("male", "Male"), ("other", "Other")], null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    province = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    dob = models.DateField(null=True, blank=True)

    BELT_CHOICES = [
        ('none', 'None'),
        ('white', 'White'),
        ('yellow', 'Yellow'),
        ('orange', 'Orange'),
        ('green', 'Green'),
        ('blue', 'Blue'),
        ('purple', 'Purple'),
        ('red', 'Red'),
        ('brown', 'Brown'),
        ('black', 'Black'),
    ]
    
    belt = models.CharField(
        max_length=10,
        choices=BELT_CHOICES,
        default='none'
    )


    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customuser_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    registration_link = models.ForeignKey(
        DojoRegistrationLink,
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='registered_users'
    )


    def __str__(self):
        return self.username

    def delete(self, *args, **kwargs):
        """
        Custom delete method to handle related object cleanup.
        """
        if self.is_student:
            self.registration_set.all().delete()  # Clean up related registrations
            self.submission_set.all().delete()   # Clean up related submissions
        elif self.is_teacher:
            self.unit_set.all().delete()         # Clean up related units

        super().delete(*args, **kwargs)

    def get_full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username


# Unit Model
class Unit(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=10)
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE, related_name='units')
    teacher = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,  # Update to SET_NULL if you want to keep the unit
        null=True,  # Allow null for this field
        blank=True,
        limit_choices_to={'is_teacher': True}
    )

    def __str__(self):
        return f"{self.name} ({self.dojo.name})"
        
    class Meta:
        unique_together = ['code', 'dojo']  # Code only has to be unique within a dojo

# Session Model
class Session(models.Model):
    name = models.CharField(max_length=50)
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE, related_name='sessions')
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    academic_year = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.dojo.name})"

    class Meta:
        verbose_name_plural = "Sessions"
        ordering = ['-start_date']
        unique_together = ['name', 'dojo']  # Session names only need to be unique within a dojo

# Registration Model
class Registration(models.Model):
    student = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,  # Update to SET_NULL
        null=True,  # Allow null for this field
        blank=True,
        limit_choices_to={'is_student': True}
    )
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.student.username if self.student else 'Unassigned'} - {self.unit.name}"


# Assignment Model
class Assignment(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    student = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='assignments',
        null=True,  
        blank=True  
    )
    title = models.CharField(max_length=255)
    due_date = models.DateTimeField(null=True, blank=True)  
    description = models.TextField()
    file = models.FileField(upload_to='assignments/', null=True, blank=True)  
    posted_at = models.DateTimeField(auto_now_add=True)
    is_submitted = models.BooleanField(default=False)

    def __str__(self):
        return self.title

class TimelineEvent(models.Model):
    EVENT_TYPES = [
        ('join', 'Join Event'),
        ('assessment', 'Assessment'),
        ('assignment', 'Assignment'),
        ('submission', 'Assignment Submission'),
        ('material', 'Learning Material'),
    ]

    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='timeline_events')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    title = models.CharField(max_length=200)
    content = models.TextField()
    assessment_result = models.CharField(max_length=50, null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_events')
    submission_file = models.FileField(upload_to='submissions/', null=True, blank=True)
    is_submitted = models.BooleanField(default=False)
    submission_date = models.DateTimeField(null=True, blank=True)
    submission_notes = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.get_event_type_display()}"

    @property
    def is_overdue(self):
        if self.event_type == 'assignment' and self.due_date:
            return timezone.now() > self.due_date
        return False
    
    @property
    def submission(self):
        return self.submissions.first() if self.event_type == 'assignment' else None

# Add after TimelineEvent model
class EventFeedback(models.Model):
    event = models.ForeignKey('TimelineEvent', on_delete=models.CASCADE, related_name='feedback')
    author = models.ForeignKey(
        'CustomUser', 
        on_delete=models.CASCADE,
        related_name='given_feedback',
        null=True  # Temporarily allow null
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Feedback on {self.event.title} by {self.author.get_full_name() if self.author else 'Unknown'}"

    def save(self, *args, **kwargs):
        is_new = not self.pk  # Check if this is a new feedback
        super().save(*args, **kwargs)
        
        if is_new:
            # Create notification for student when new feedback is added
            Notification.objects.create(
                user=self.event.student,
                title=f"New feedback on {self.event.title}",
                message=f"{self.author.get_full_name()} added feedback to your {self.event.get_event_type_display().lower()}",
                notification_type='feedback',
                link=f'/assignments/#{self.event.id}'
            )

class Notification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=200, blank=True)
    notification_type = models.CharField(max_length=50, default='feedback')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"

# Submission Model

class Submission(models.Model):
    assignment = models.ForeignKey(
        TimelineEvent, 
        on_delete=models.CASCADE,
        related_name='submissions'
    )
    student = models.ForeignKey(
        'CustomUser', 
        on_delete=models.CASCADE,
        limit_choices_to={'is_student': True},  # Only allow students
        null=False,  # Make it non-nullable
        default=1  # Set a default value - use the ID of a default student account
    )
    file = models.FileField(upload_to='submissions/')
    notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.student.username} - {self.assignment.title}"

class Attendance(models.Model):
    ATTENDANCE_STATUS = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
    ]
    
    student = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='attendances',
        limit_choices_to={'is_student': True}
    )
    unit = models.ForeignKey(
        Unit, 
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    date = models.DateField(default=timezone.now)
    status = models.CharField(
        max_length=10,
        choices=ATTENDANCE_STATUS,
        default='present'
    )
    notes = models.TextField(blank=True, null=True)
    marked_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        related_name='marked_attendances',
        null=True,
        limit_choices_to={'is_teacher': True}
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['student', 'unit', 'date']
        ordering = ['-date', 'unit']
        
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.unit.name} - {self.date} - {self.get_status_display()}"
    
    @classmethod
    def get_attendance_stats(cls, student_id, unit_id=None):
        """Get attendance statistics for a student, filtered by unit"""
        query = cls.objects.filter(student_id=student_id)
        if unit_id:
            query = query.filter(unit_id=unit_id)
        
        total_classes = query.count()
        present_count = query.filter(status='present').count()
        absent_count = query.filter(status='absent').count()
        late_count = query.filter(status='late').count()
        
        return {
            'total': total_classes,
            'present': present_count,
            'absent': absent_count,
            'late': late_count,
            'attendance_rate': round((present_count + late_count) / total_classes * 100, 1) if total_classes else 0
        }

class FeedbackTemplate(models.Model):
    CATEGORY_CHOICES = [
        ('strengths', 'Strengths'),
        ('growth', 'Areas for Growth'),
        ('next_steps', 'Next Steps'),
    ]
    
    title = models.CharField(max_length=100)
    content = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='strengths')
    created_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='feedback_templates'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'title']
        
    def __str__(self):
        return self.title

class BeltCriteria(models.Model):
    belt = models.CharField(max_length=10, choices=CustomUser.BELT_CHOICES)
    title = models.CharField(max_length=50)
    description = models.TextField()
    all_belts = models.BooleanField(default=False, help_text="Apply this criteria to all belt levels")
    order = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_criteria'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'title']
        verbose_name_plural = "Belt Criteria"
        
    def __str__(self):
        return f"{self.title} - {self.get_belt_display()}"
    
    def get_belt_display(self):
        for value, label in CustomUser.BELT_CHOICES:
            if value == self.belt:
                return label
        return self.belt

class StudentCriteriaProgress(models.Model):
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='criteria_progress')
    criteria = models.ForeignKey(BeltCriteria, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    completed_date = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='marked_criteria')
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ['student', 'criteria']
        
    def __str__(self):
        status = 'Completed' if self.completed else 'Incomplete'
        return f"{self.student.username} - {self.criteria.title} - {status}"

class CalendarEvent(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True)
    all_day = models.BooleanField(default=False)
    background_color = models.CharField(max_length=20, default='#3c8dbc')
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, 
                                  related_name='created_calendar_events') 
    
    repeats = models.BooleanField(default=False)
    repeat_until = models.DateField(blank=True, null=True)
    
    is_birthday = models.BooleanField(default=False)
    is_auto_generated = models.BooleanField(default=False)
    related_user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, 
                                    related_name='related_events')
    
    # Add new visibility fields
    VISIBILITY_CHOICES = [
        ('all', 'All Students'),
        ('classes', 'Specific Classes'),
        ('students', 'Specific Students'),
    ]
    visibility_type = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='all')
    visible_to_classes = models.ManyToManyField('Unit', related_name='calendar_events', blank=True)
    visible_to_students = models.ManyToManyField('CustomUser', related_name='visible_events', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    @classmethod
    def generate_birthday_events(cls):
        """Generate birthday events for all users with birthdays"""

        cls.objects.filter(is_birthday=True, is_auto_generated=True).delete()
        

        users = CustomUser.objects.exclude(dob__isnull=True)
        
        created_count = 0
        current_year = timezone.now().year
        
        for user in users:

            if user.dob:
                try:

                    birthday_this_year = datetime.datetime.combine(
                        datetime.date(current_year, user.dob.month, user.dob.day),
                        datetime.time(9, 0)  # 9 AM
                    )
                    

                    cls.objects.create(
                        title=f"{user.get_full_name()}'s Birthday",
                        description=f"Birthday celebration for {user.get_full_name()}",
                        start_time=timezone.make_aware(birthday_this_year),
                        all_day=True,
                        is_birthday=True,  # Use is_birthday instead of event_type
                        background_color='#dc3545',  # Red color for birthdays
                        is_auto_generated=True,
                        related_user=user,
                        created_by=CustomUser.objects.filter(is_staff=True).first() or user  # Fallback to the user if no staff
                    )
                    created_count += 1
                except Exception as e:
                    continue
        
        return created_count

    def is_visible_to_user(self, user):
        """Check if event is visible to a specific user"""
        # Instructors can see all events
        if user.is_staff or user.is_teacher:
            return True
            
        # Auto-generated events like birthdays are visible to everyone
        if self.is_auto_generated:
            return True
            
        # Check visibility settings
        if self.visibility_type == 'all':
            return True
        elif self.visibility_type == 'classes':
            # Check if user is in any of the visible classes
            return Registration.objects.filter(
                student=user, 
                unit__in=self.visible_to_classes.all()
            ).exists()
        elif self.visibility_type == 'students':
            # Check if user is in the visible students list
            return self.visible_to_students.filter(id=user.id).exists()
            
        return False


