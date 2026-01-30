"""
Models for credential documents
"""
from django.db import models
from django.core.validators import FileExtensionValidator
import uuid


class ProofTypeChoices(models.TextChoices):
    CERTIFICATE = 'certificate', 'Certificate'
    JOB_HISTORY = 'job_history', 'Job History'
    SKILL = 'skill', 'Skill'
    MILESTONE = 'milestone', 'Milestone'
    COMMUNITY = 'community', 'Community Contribution'


class Document(models.Model):
    """Base model for all credential documents"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proof_type = models.CharField(max_length=20, choices=ProofTypeChoices.choices)
    internal_id = models.CharField(max_length=100, unique=True)
    validation_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Store onchain data as JSON
    onchain_data = models.JSONField()
    
    # Metadata
    user_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('verified', 'Verified'),
            ('rejected', 'Rejected'),
        ],
        default='pending'
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['proof_type', 'created_at']),
            models.Index(fields=['user_id', 'proof_type']),
            models.Index(fields=['internal_id']),
        ]
    
    def __str__(self):
        return f"{self.proof_type} - {self.internal_id}"


class Certificate(models.Model):
    """Certificate/Training credentials"""
    document = models.OneToOneField(Document, on_delete=models.CASCADE, related_name='certificate')
    certificate_title = models.CharField(max_length=255)
    issuer_name = models.CharField(max_length=255)
    completion_date = models.CharField(max_length=7)  # YYYY-MM format
    credential_type = models.CharField(
        max_length=20,
        choices=[
            ('Course', 'Course'),
            ('Bootcamp', 'Bootcamp'),
            ('Workshop', 'Workshop'),
            ('Award', 'Award'),
        ]
    )
    program_category = models.CharField(max_length=100)
    
    class Meta:
        ordering = ['-completion_date']
    
    def __str__(self):
        return f"{self.certificate_title} - {self.issuer_name}"


class JobHistory(models.Model):
    """Work experience records"""
    document = models.OneToOneField(Document, on_delete=models.CASCADE, related_name='job_history')
    job_title = models.CharField(max_length=255)
    employer_name = models.CharField(max_length=255)
    employment_type = models.CharField(
        max_length=20,
        choices=[
            ('full-time', 'Full-time'),
            ('part-time', 'Part-time'),
            ('intern', 'Intern'),
            ('contributor', 'Contributor'),
            ('contract', 'Contract'),
        ]
    )
    start_date = models.CharField(max_length=7)  # YYYY-MM format
    end_date = models.CharField(max_length=7, blank=True, null=True)  # YYYY-MM format
    job_category = models.CharField(max_length=100)
    
    class Meta:
        ordering = ['-start_date']
        verbose_name_plural = 'Job histories'
    
    def __str__(self):
        return f"{self.job_title} at {self.employer_name}"


class Skill(models.Model):
    """Skills and competencies"""
    document = models.OneToOneField(Document, on_delete=models.CASCADE, related_name='skill')
    skill_name = models.CharField(max_length=100)
    skill_category = models.CharField(max_length=100)
    proficiency_level = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
        ],
        blank=True,
        null=True
    )
    
    class Meta:
        ordering = ['skill_category', 'skill_name']
    
    def __str__(self):
        return f"{self.skill_name} ({self.skill_category})"


class Milestone(models.Model):
    """Career milestones and achievements"""
    document = models.OneToOneField(Document, on_delete=models.CASCADE, related_name='milestone')
    milestone_type = models.CharField(
        max_length=20,
        choices=[
            ('Promotion', 'Promotion'),
            ('Award', 'Award'),
            ('Recognition', 'Recognition'),
            ('Key Result', 'Key Result'),
        ]
    )
    issuer_name = models.CharField(max_length=255)
    date = models.CharField(max_length=7)  # YYYY-MM format
    milestone_summary = models.TextField()
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.milestone_type} - {self.issuer_name}"


class CommunityContribution(models.Model):
    """Community contributions and public work"""
    document = models.OneToOneField(Document, on_delete=models.CASCADE, related_name='community_contribution')
    contribution_type = models.CharField(
        max_length=20,
        choices=[
            ('Talk', 'Talk'),
            ('Article', 'Article'),
            ('Open Source', 'Open Source'),
            ('Community Role', 'Community Role'),
        ]
    )
    platform_name = models.CharField(max_length=255)
    date = models.CharField(max_length=7)  # YYYY-MM format
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.contribution_type} on {self.platform_name}"


class EvidenceFile(models.Model):
    """Evidence files attached to documents"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='evidence_files')
    file = models.FileField(
        upload_to='evidence/%Y/%m/%d/',
        validators=[FileExtensionValidator(
            allowed_extensions=['pdf', 'png', 'jpg', 'jpeg', 'gif', 'txt', 'doc', 'docx']
        )]
    )
    file_type = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_size = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"Evidence for {self.document.internal_id}"
    
    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)
