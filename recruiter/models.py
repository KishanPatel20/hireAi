from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from candidate.models import Candidate  # Add this import at the top

class RecruiterProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    industry = models.CharField(max_length=100, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    company_size = models.CharField(max_length=50, blank=True, null=True)
    founded = models.CharField(max_length=10, blank=True, null=True)
    headquarters = models.CharField(max_length=255, blank=True, null=True)
    company_description = models.TextField(blank=True, null=True)
    job_title = models.CharField(max_length=255, blank=True, null=True)
    years_of_experience = models.CharField(max_length=10, blank=True, null=True)
    linkedin_profile = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.company_name}"

class Department(models.Model):
    name = models.CharField(max_length=100)
    recruiter = models.ForeignKey(RecruiterProfile, on_delete=models.CASCADE)
    description = models.TextField(blank=True, null=True)
    head_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('name', 'recruiter')

    def __str__(self):
        return f"{self.name} - {self.recruiter.company_name}"

class ActiveRole(models.Model):
    LEVEL_CHOICES = [
        ('Junior', 'Junior'),
        ('Mid', 'Mid'),
        ('Senior', 'Senior'),
    ]
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]
    title = models.CharField(max_length=255)
    recruiter = models.ForeignKey(RecruiterProfile, on_delete=models.CASCADE)
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='Mid')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('title', 'recruiter')

    def __str__(self):
        return f"{self.title} - {self.recruiter.company_name}"

class Workflow(models.Model):
    recruiter = models.ForeignKey(RecruiterProfile, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    initial_user_request = models.TextField()
    system_response_summary = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('name', 'recruiter')

    def clean(self):
        # Check if recruiter has reached the limit of 3 workflows
        if not self.pk:  # Only check for new workflows
            if Workflow.objects.filter(recruiter=self.recruiter).count() >= 3:
                raise ValidationError("You have reached your maximum workflow limit (3).")

    def __str__(self):
        return f"{self.name} - {self.recruiter.company_name}"

class ConversationTurn(models.Model):
    SENDER_CHOICES = [
        ('user', 'User'),
        ('system', 'System')
    ]

    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE)
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    message_content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender} - {self.workflow.name} - {self.timestamp}"

class SelectedCandidate(models.Model):
    recruiter = models.ForeignKey(RecruiterProfile, on_delete=models.CASCADE, related_name='selected_candidates')
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='selected_by_recruiters')
    selected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('recruiter', 'candidate')

    def __str__(self):
        return f"{self.recruiter} selected {self.candidate}"
