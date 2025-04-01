from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class CustomUser(AbstractUser):
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    
    # Add role-based fields
    is_student = models.BooleanField(default=False)  # To identify students
    is_teacher = models.BooleanField(default=False)  # To identify teachers

    gender = models.CharField(max_length=10, choices=[("female", "Female"), ("male", "Male"), ("other", "Other")], null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
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

    # Add related_name for groups and user_permissions to avoid conflicts
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
    code = models.CharField(max_length=10, unique=True)
    teacher = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,  # Update to SET_NULL if you want to keep the unit
        null=True,  # Allow null for this field
        blank=True,
        limit_choices_to={'is_teacher': True}
    )

    def __str__(self):
        return self.name

# Session Model
class Session(models.Model):
    name = models.CharField(max_length=50, unique=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    
    # Optional: Add a reference to the academic year or semester
    academic_year = models.CharField(max_length=20, blank=True, null=True)
    
    # Optional: Add a status field
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"

    class Meta:
        verbose_name_plural = "Sessions"
        ordering = ['-start_date']

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



