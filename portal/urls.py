from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from . import views

from django.contrib.auth import views as auth_views

urlpatterns = [
    # Authentication
    path('', views.user_login, name='login'),
    path('', views.user_logout, name='logout'),
    path('register/', views.register, name='register'),

    path('register/student/', views.register_student, name='register_student'),
    path('register/teacher/', views.register_teacher, name='register_teacher'),

    # Dashboards
    path('student_dashboard/', views.student_dashboard, name='student_dashboard'),
    path('teacher_dashboard/', views.teacher_dashboard, name='teacher_dashboard'),

    # Student Views
    path('register_units/', views.register_units, name='register_units'),
    path('submit_assignment/<int:assignment_id>/', views.submit_assignment, name='submit_assignment'),
    path('report_session/', views.report_session, name='report_session'),
    path('assignment/<int:event_id>/submit/', views.submit_assignment, name='submit_assignment'),

    # Teacher Views
    path('post_assignment/', views.post_assignment, name='post_assignment'),
    path('students_in_unit/<int:unit_id>/', views.students_in_unit, name='students_in_unit'),
    path('view_submissions/<int:assignment_id>/', views.view_submissions, name='view_submissions'),

    # Admin Views
    path('student_list/<int:unit_id>/', views.admin_student_list, name='admin_student_list'),
    path('student/<int:student_id>/', views.admin_student_info, name='admin_student_info'),

    path('student/<int:student_id>/change-belt/', views.change_belt, name='change_belt'),
    path('student/<int:student_id>/add-event/', views.add_timeline_event, name='add_timeline_event'),

    # Assignment Views
    path('assignments/', views.view_assignment, name='assignments'),

    

    # View Student views

    # path('assignments/', views.view_assignment, name='assignments'),

    # Student progress views
    path('student_progress/', views.student_progress, name='student_progress'),



    path('', views.index),
    path('dashboard-v1/', views.index, name='dashboardv1'),
    path('dashboard-v2/', views.index2, name='dashboardv2'),
    path('dashboard-v3/', views.index3, name='dashboardv3'),
    path('widgets/', views.widgets, name='widgets'),
    path('profile/', views.profile, name='profile'),

    # Examples
    path('examples/calendar/', views.examples_calendar, name='examples_calendar'),
    path('examples/gallery/', views.examples_gallery, name='examples_gallery'),
    path('examples/kanban/', views.examples_kanban, name='examples_kanban'),
    path('examples/invoice/', views.examples_invoice, name='examples_invoice'),
    path('invoice-print/', views.invoice_print, name='invoice_print'),
    path('examples/profile/', views.examples_profile, name='examples_profile'),
    path('examples/e-commerce/', views.examples_e_commerce, name='examples_e_commerce'),
    path('examples/projects/', views.examples_projects, name='examples_projects'),
    path('examples/project-add/', views.examples_project_add, name='examples_project_add'),
    path('examples/project-edit/', views.examples_project_edit, name='examples_project_edit'),
    path('examples/project-detail/', views.examples_project_detail, name='examples_project_detail'),
    path('examples/contacts/', views.examples_contacts, name='examples_contacts'),
    path('examples/faq/', views.examples_faq, name='examples_faq'),
    path('examples/contact-us/', views.examples_contact_us, name='examples_contact_us'),

    # Extra 
    path('login-v1/', views.UserLoginViewV1.as_view(), name='login_v1'),
    path('login-v2/', views.UserLoginViewV2.as_view(), name='login_v2'),
    path('registration-v1/', views.register_v1, name='registration_v1'),
    path('registration-v2/', views.register_v2, name='registration_v2'),
    path('forgot-password-v1/', views.UserPasswordResetViewV1.as_view(), name='forgot_password_v1'),
    path('forgot-password-v2/', views.UserPasswordResetViewV2.as_view(), name='forgot_password_v2'),
    path('recover-password-v1/', views.UserPasswordChangeViewV1.as_view(), name='recover_password_v1'),
    path('recover-password-v2/', views.UserPasswordChangeViewV2.as_view(), name='recover_password_v2'),
    path('lockscreen/', views.lockscreen, name='lockscreen'),
    path('legacy-user-menu/', views.legacy_user_menu, name='legacy_user_menu'),
    path('language-menu/', views.language_menu, name='language_menu'),
    path('error-404/', views.error_404, name='error_404'),
    path('error-500/', views.error_500, name='error_500'),
    path('pace/', views.pace, name='pace'),
    path('blank-page/', views.blank_page, name='blank_page'),
    path('starter-page/', views.starter_page, name='starter_page'),

    # Search
    path('search-simple/', views.search_simple, name='search_simple'),
    path('search-enhanced/', views.search_enhanced, name='search_enhanced'),
    path('simple-result/', views.simple_results, name='simple_results'),
    path('enhanced-result/', views.enhanced_results, name='enhanced_results'),

    path('iframe/', views.iframe, name='iframe'),



    # Mailbox
    path('mailbox/inbox/', views.mailbox_inbox, name='mailbox_inbox'),
    path('mailbox/compose/', views.mailbox_compose, name='mailbox_compose'),
    path('mailbox/read-mail/', views.mailbox_read_mail, name='mailbox_read_mail'),

    # Charts
    path('chartjs/', views.chartjs, name='chartjs'),
    path('flot/', views.flot, name='flot'),
    path('inline/', views.inline, name='inline'),
    path('uplot/', views.uplot, name='uplot'),

    # UI Elements
    path('ui/general/', views.ui_general, name='ui_general'),
    path('ui/icons/', views.ui_icons, name='ui_icons'),
    path('ui/buttons/', views.ui_buttons, name='ui_buttons'),
    path('ui/sliders/', views.ui_sliders, name='ui_sliders'),
    path('ui/modals-alerts/', views.ui_modals_alerts, name='ui_modals_alerts'),
    path('ui/navbar-tabs/', views.ui_navbar_tabs, name='ui_navbar_tabs'),
    path('ui/timeline/', views.ui_timeline, name='ui_timeline'),
    path('ui/ribbons/', views.ui_ribbons, name='ui_ribbons'),

    # Forms
     path('form/general/', views.form_general, name='form_general'),
     path('form/advanced/', views.form_advanced, name='form_advanced'),
     path('form/editors/', views.form_editors, name='form_editors'),
     path('form/validation/', views.form_validation, name='form_validation'),

     # Table
     path('table/simple/', views.table_simple, name='table_simple'),
     path('table/data/', views.table_data, name='table_data'),
     path('table/jsgrid/', views.table_jsgrid, name='table_jsgrid'),

    #Layouts
    path('top-navigation/', views.top_navigation, name='top_navigation'),
    path('top-nav-sidebar/', views.top_nav_sidebar, name='top_nav_sidebar'),
    path('boxed/', views.boxed, name='boxed'),
    path('fixed-sidebar/', views.fixed_sidebar, name='fixed_sidebar'),
    path('fixed-sidebar-custom/', views.fixed_sidebar_custom, name='fixed_sidebar_custom'),
    path('fixed-topnav/', views.fixed_topnav, name='fixed_topnav'),
    path('fixed-footer/', views.fixed_footer, name='fixed_footer'),
    path('collapsed-sidebar/', views.collapsed_sidebar, name='collapsed_sidebar'),

    # Authentication
    path('accounts/register/', views.register, name='register'),
    # path('accounts/login/', views.UserLoginView.as_view(), name='login'),
    path('', views.user_logout_view, name='logout'),
    path('accounts/password-change/', views.UserPasswordChangeView.as_view(), name='password_change'),
    path('accounts/password-change-done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='accounts/password_change_done.html'
    ), name="password_change_done" ),
    path('accounts/password-reset/', views.UserPasswordResetView.as_view(), name='password_reset'),
    path('accounts/password-reset-confirm/<uidb64>/<token>/', 
        views.UserPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('accounts/password-reset-done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    path('accounts/password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


