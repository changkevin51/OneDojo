from django.contrib import admin
from .models import *  # Import all models from your app
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.admin import SimpleListFilter

# Registration Form with validation to prevent duplicate registrations
class RegistrationForm(forms.ModelForm):
    class Meta:
        model = Registration
        fields = ['student', 'unit', 'session']

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        unit = cleaned_data.get('unit')
        session = cleaned_data.get('session')
        
        # Only perform the check if all related instances are saved.
        if student and unit and session:
            if not (student.pk and unit.pk and session.pk):
                # Skip duplicate checking if any instance is not saved yet.
                return cleaned_data

            if Registration.objects.filter(student=student, unit=unit, session=session).exists():
                raise forms.ValidationError("This registration already exists.")
        return cleaned_data

# Registration Inline with updated form
class RegistrationInline(admin.TabularInline):
    model = Registration
    form = RegistrationForm
    extra = 1
    fields = ['student', 'session', 'unit']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(unit__isnull=True)  # Filter registrations without a unit


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'teacher']
    search_fields = ['name', 'code']
    list_filter = ['teacher']
    inlines = [RegistrationInline]

class StudentGenderFilter(SimpleListFilter):
    title = 'Gender'
    parameter_name = 'student_gender'

    def lookups(self, request, model_admin):
        # Provide filter options
        return [
            ('Male', 'Male'),
            ('Female', 'Female'),
            ('Other', 'Other'),
        ]

    def queryset(self, request, queryset):
        # Filter based on the selected gender
        if self.value() == 'Male':
            return queryset.filter(student__gender='Male')
        elif self.value() == 'Female':
            return queryset.filter(student__gender='Female')
        elif self.value() == 'Other':
            return queryset.filter(student__gender='Other')
        return queryset


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    form = RegistrationForm
    list_display = ['student', 'unit', 'session', 'get_student_gender', 'get_student_city']
    search_fields = ['student__username', 'unit__name', 'session__name', 'student__email']
    list_filter = ['unit', 'session', StudentGenderFilter]  # Use the custom filter
    list_select_related = ['student', 'unit', 'session']
    raw_id_fields = ['student', 'unit', 'session']

    fieldsets = (
        (None, {'fields': ('student', 'unit', 'session')}),
        ('Additional Info', {'fields': ('get_student_gender', 'get_student_city')}),
    )
    readonly_fields = ['get_student_gender', 'get_student_city']  # Make computed fields read-only

    def get_student_gender(self, obj):
        return obj.student.gender if obj.student else "N/A"
    get_student_gender.short_description = 'Gender'

    def get_student_city(self, obj):
        return obj.student.city if obj.student else "N/A"
    get_student_city.short_description = 'City'

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing registration
            return ['student']  # Make student read-only
        return []

    def delete_queryset(self, request, queryset):
        for registration in queryset:
            if registration.student and Submission.objects.filter(student=registration.student).exists():
                raise ValidationError(
                    f"Cannot delete registration for {registration.student.username} due to related submissions."
                )
        super().delete_queryset(request, queryset)

    def has_delete_permission(self, request, obj=None):
        if obj and Submission.objects.filter(student=obj.student).exists():
            self.message_user(
                request,
                f"Cannot delete registration for {obj.student.username}: Related submissions exist.",
                level='error'
            )
            return False
        return True


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'is_student', 'is_teacher', 'gender', 'city']
    search_fields = ['username', 'email', 'city']
    list_filter = ['is_student', 'is_teacher', 'gender', 'city']
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'profile_picture', 'gender', 'dob', 'address', 'province', 'city')}),
        ('Roles and Permissions', {'fields': ('is_student', 'is_teacher', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    readonly_fields = ['last_login', 'date_joined']


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'is_active']
    search_fields = ['name']
    list_filter = ['is_active']
    ordering = ['-start_date']


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'unit', 'posted_at']
    search_fields = ['title', 'unit__name']
    list_filter = ['unit', 'posted_at']


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['assignment', 'student', 'submitted_at']
    search_fields = ['assignment__title', 'student__username']
    list_filter = ['assignment', 'submitted_at']
    list_select_related = ['assignment', 'student']  # Optimize queries