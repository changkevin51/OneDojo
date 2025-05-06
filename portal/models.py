from django.contrib.auth.models import AbstractUser, User
from django.db import models
from django.utils import timezone
from django.conf import settings
import datetime
import time
import random
import string
import uuid

# dojo model
class Dojo(models.Model):
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
        """get count of students in this dojo"""
        return CustomUser.objects.filter(dojo=self, is_student=True).count()
    
    def get_instructor_count(self):
        """get count of instructors in this dojo"""
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
        """check if link is valid"""
        if not self.is_active:
            return False
        if self.expiration_date and timezone.now() > self.expiration_date:
            return False
        return True
    
    @property
    def uses_count(self):
        """get number of users who registered with this link"""
        return CustomUser.objects.filter(registration_link=self).count()
    
    @property
    def expires_at(self):
        return self.expiration_date
    
    def save(self, *args, **kwargs):
        """save registration link, generate code if missing"""
        if not self.code:
            self.code = str(uuid.uuid4())[:8]
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_code():
        """make a random 8-char code"""
        import random
        import string
        characters = string.ascii_uppercase + string.digits
        code = ''.join(random.choice(characters) for _ in range(8))
        return code

# user model
class CustomUser(AbstractUser):
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    dojo = models.ForeignKey(Dojo, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    is_student = models.BooleanField(default=False)
    is_teacher = models.BooleanField(default=False)
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
        """delete user and related stuff"""
        if self.is_student:
            self.registration_set.all().delete()
            self.submission_set.all().delete()
        elif self.is_teacher:
            self.unit_set.all().delete()
        super().delete(*args, **kwargs)

    def get_full_name(self):
        """get full name or username"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

# unit model
class Unit(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=10)
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE, related_name='units')
    teacher = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'is_teacher': True}
    )

    def __str__(self):
        return f"{self.name} ({self.dojo.name})"
        
    class Meta:
        unique_together = ['code', 'dojo']

# session model
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
        unique_together = ['name', 'dojo']

# registration model
class Registration(models.Model):
    student = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'is_student': True}
    )
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.student.username if self.student else 'Unassigned'} - {self.unit.name}"

# assignment model
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

# timeline event model
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
        """check if assignment is overdue"""
        if self.event_type == 'assignment' and self.due_date:
            return timezone.now() > self.due_date
        return False
    
    @property
    def submission(self):
        """get first submission if assignment"""
        return self.submissions.first() if self.event_type == 'assignment' else None

# feedback on timeline event
class EventFeedback(models.Model):
    event = models.ForeignKey('TimelineEvent', on_delete=models.CASCADE, related_name='feedback')
    author = models.ForeignKey(
        'CustomUser', 
        on_delete=models.CASCADE,
        related_name='given_feedback',
        null=True
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Feedback on {self.event.title} by {self.author.get_full_name() if self.author else 'Unknown'}"

    def save(self, *args, **kwargs):
        """save feedback and notify student if new"""
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new:
            Notification.objects.create(
                user=self.event.student,
                title=f"New feedback on {self.event.title}",
                message=f"{self.author.get_full_name()} added feedback to your {self.event.get_event_type_display().lower()}",
                notification_type='feedback',
                link=f'/assignments/#{self.event.id}'
            )

# notification model
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

# submission model
class Submission(models.Model):
    assignment = models.ForeignKey(
        TimelineEvent, 
        on_delete=models.CASCADE,
        related_name='submissions'
    )
    student = models.ForeignKey(
        'CustomUser', 
        on_delete=models.CASCADE,
        limit_choices_to={'is_student': True},
        null=False,
        default=1
    )
    file = models.FileField(upload_to='submissions/')
    notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.student.username} - {self.assignment.title}"

# attendance model
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
        """get attendance stats for a student"""
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

# feedback template model
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

# belt criteria model
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
        """get belt label"""
        for value, label in CustomUser.BELT_CHOICES:
            if value == self.belt:
                return label
        return self.belt

# student progress on belt criteria
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

# calendar event model
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
        """make birthday events for all users with birthdays"""
        cls.objects.filter(is_birthday=True, is_auto_generated=True).delete()
        users = CustomUser.objects.exclude(dob__isnull=True)
        created_count = 0
        current_year = timezone.now().year
        for user in users:
            if user.dob:
                try:
                    birthday_this_year = datetime.datetime.combine(
                        datetime.date(current_year, user.dob.month, user.dob.day),
                        datetime.time(9, 0)
                    )
                    cls.objects.create(
                        title=f"{user.get_full_name()}'s Birthday",
                        description=f"Birthday celebration for {user.get_full_name()}",
                        start_time=timezone.make_aware(birthday_this_year),
                        all_day=True,
                        is_birthday=True,
                        background_color='#dc3545',
                        is_auto_generated=True,
                        related_user=user,
                        created_by=CustomUser.objects.filter(is_staff=True).first() or user
                    )
                    created_count += 1
                except Exception as e:
                    continue
        return created_count

    def is_visible_to_user(self, user):
        """check if event is visible to a user"""
        if user.is_staff or user.is_teacher:
            return True
        if self.is_auto_generated:
            return True
        if self.visibility_type == 'all':
            return True
        elif self.visibility_type == 'classes':
            return Registration.objects.filter(
                student=user, 
                unit__in=self.visible_to_classes.all()
            ).exists()
        elif self.visibility_type == 'students':
            return self.visible_to_students.filter(id=user.id).exists()
        return False


