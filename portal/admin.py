from django.contrib import admin
from .models import *  # Import all models from your app
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.admin import SimpleListFilter
from django.contrib.admin import AdminSite
from django.db.models import Count
from django.utils.html import format_html

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
        
        # Check if unit and session belong to the same dojo
        if unit and session and unit.dojo != session.dojo:
            raise forms.ValidationError("Unit and session must belong to the same dojo.")
            
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

# Dojo Admin
@admin.register(Dojo)
class DojoAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'province', 'student_count', 'instructor_count']
    search_fields = ['name', 'city', 'province']
    
    def student_count(self, obj):
        return obj.get_student_count()
    student_count.short_description = 'Students'
    
    def instructor_count(self, obj):
        return obj.get_instructor_count()
    instructor_count.short_description = 'Instructors'

# DojoFilter for filtering by dojo
class DojoFilter(SimpleListFilter):
    title = 'Dojo'
    parameter_name = 'dojo'
    
    def lookups(self, request, model_admin):
        return [(dojo.id, dojo.name) for dojo in Dojo.objects.all()]
    
    def queryset(self, request, queryset):
        if self.value():
            if hasattr(queryset.model, 'dojo'):
                return queryset.filter(dojo_id=self.value())
            elif hasattr(queryset.model, 'unit'):
                return queryset.filter(unit__dojo_id=self.value())
            elif hasattr(queryset.model, 'student'):
                return queryset.filter(student__dojo_id=self.value())
        return queryset

@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'teacher', 'dojo']
    search_fields = ['name', 'code']
    list_filter = ['teacher', DojoFilter]
    inlines = [RegistrationInline]
    
    def get_context_data(self, request, obj=None, **kwargs):
        context = super().get_context_data(request, obj, **kwargs)
        if obj:  # If this is a change form
            context['unit_students'] = obj.students.all()
        return context
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'teacher':
            kwargs["queryset"] = CustomUser.objects.filter(is_teacher=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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
    list_filter = ['unit', 'session', StudentGenderFilter, DojoFilter]  # Use the custom filter
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

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Filter session and unit dropdowns to match the selected dojo
        if db_field.name == "unit" and request.GET.get('dojo'):
            kwargs["queryset"] = Unit.objects.filter(dojo_id=request.GET.get('dojo'))
        elif db_field.name == "session" and request.GET.get('dojo'):
            kwargs["queryset"] = Session.objects.filter(dojo_id=request.GET.get('dojo'))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# Add dojo field to CustomUserAdmin
class DojoListFilter(SimpleListFilter):
    title = 'Dojo'
    parameter_name = 'dojo'
    
    def lookups(self, request, model_admin):
        return [(dojo.id, dojo.name) for dojo in Dojo.objects.all()]
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(dojo_id=self.value())
        return queryset

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'dojo', 'is_student', 'is_teacher', 'gender', 'city']
    search_fields = ['username', 'email', 'city', 'first_name', 'last_name']
    list_filter = ['is_student', 'is_teacher', 'gender', 'city', DojoListFilter]
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Dojo', {'fields': ('dojo',)}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'profile_picture', 'gender', 'dob', 'address', 'province', 'city')}),
        ('Roles and Permissions', {'fields': ('is_student', 'is_teacher', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    readonly_fields = ['last_login', 'date_joined']
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Superusers can edit any dojo, others can only set users to their own dojo
        if not request.user.is_superuser and request.user.dojo and 'dojo' in form.base_fields:
            form.base_fields['dojo'].initial = request.user.dojo
            form.base_fields['dojo'].widget.attrs['disabled'] = 'disabled'
        return form
        
    def save_model(self, request, obj, form, change):
        # If non-superuser is trying to add a user, automatically assign to their dojo
        if not request.user.is_superuser and not obj.dojo:
            obj.dojo = request.user.dojo
        super().save_model(request, obj, form, change)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'dojo', 'start_date', 'end_date', 'is_active']
    search_fields = ['name']
    list_filter = ['is_active', DojoFilter]
    ordering = ['-start_date']


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'unit', 'posted_at']
    search_fields = ['title', 'unit__name']
    list_filter = ['unit', 'posted_at', DojoFilter]
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "unit" and request.user.dojo and not request.user.is_superuser:
            kwargs["queryset"] = Unit.objects.filter(dojo=request.user.dojo)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['assignment', 'student', 'submitted_at']
    search_fields = ['assignment__title', 'student__username']
    list_filter = ['assignment', 'submitted_at']
    list_select_related = ['assignment', 'student']  # Optimize queries

@admin.register(DojoRegistrationLink)
class DojoRegistrationLinkAdmin(admin.ModelAdmin):
    list_display = ['code', 'dojo', 'description', 'is_active', 'uses_count', 'max_uses', 'expires_at', 'created_at']
    list_filter = ['is_active', DojoFilter]
    search_fields = ['code', 'description', 'dojo__name']
    readonly_fields = ['code', 'uses_count', 'created_at']
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing link
            return self.readonly_fields + ['dojo']  # Can't change dojo after creation
        return self.readonly_fields
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:  # New object being created
            obj.code = DojoRegistrationLink.generate_code()
            if not request.user.is_superuser:
                obj.dojo = request.user.dojo  # Set dojo to user's dojo for non-superusers
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "dojo" and not request.user.is_superuser and request.user.dojo:
            kwargs["queryset"] = Dojo.objects.filter(id=request.user.dojo.id)
            kwargs["initial"] = request.user.dojo
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class MyAdminSite(AdminSite):
    site_header = "My Admin Dashboard"
    site_title = "My Admin Panel"
    index_title = "Dashboard"

    def index(self, request, extra_context=None):
        from .models import Unit  # import here to avoid circular imports
        units = Unit.objects.all().annotate(
            student_count=Count('registration__student', distinct=True)
        ).prefetch_related('teacher')
        if extra_context is None:
            extra_context = {}
        extra_context['units'] = units
        return super().index(request, extra_context=extra_context)
# Instantiate and register models with the new admin site.
my_admin_site = MyAdminSite(name='myadmin')
# Instead of using decorators, manually register your models:
from .models import Unit, Registration, CustomUser, Session, Assignment, Submission, Dojo, DojoRegistrationLink
# Also import the existing admin classes
my_admin_site.register(Dojo, DojoAdmin)
my_admin_site.register(Unit, UnitAdmin)
my_admin_site.register(Registration, RegistrationAdmin)
my_admin_site.register(CustomUser, CustomUserAdmin)
my_admin_site.register(Session, SessionAdmin)
my_admin_site.register(Assignment, AssignmentAdmin)
my_admin_site.register(Submission, SubmissionAdmin)
my_admin_site.register(DojoRegistrationLink, DojoRegistrationLinkAdmin)