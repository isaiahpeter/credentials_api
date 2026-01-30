# Register your models here.
"""
Admin configuration for documents app
"""
from django.contrib import admin
from .models import (
    Document, Certificate, JobHistory, Skill,
    Milestone, CommunityContribution, EvidenceFile
)


class EvidenceFileInline(admin.TabularInline):
    model = EvidenceFile
    extra = 0
    readonly_fields = ('uploaded_at', 'file_size')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('internal_id', 'proof_type', 'user_id', 'status', 'created_at')
    list_filter = ('proof_type', 'status', 'created_at')
    search_fields = ('internal_id', 'user_id', 'validation_hash')
    readonly_fields = ('id', 'internal_id', 'validation_hash', 'created_at', 'updated_at')
    inlines = [EvidenceFileInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'proof_type', 'internal_id', 'validation_hash')
        }),
        ('Status', {
            'fields': ('status', 'user_id')
        }),
        ('Data', {
            'fields': ('onchain_data',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('certificate_title', 'issuer_name', 'completion_date', 'credential_type')
    list_filter = ('credential_type', 'completion_date')
    search_fields = ('certificate_title', 'issuer_name', 'program_category')
    readonly_fields = ('document',)


@admin.register(JobHistory)
class JobHistoryAdmin(admin.ModelAdmin):
    list_display = ('job_title', 'employer_name', 'employment_type', 'start_date', 'end_date')
    list_filter = ('employment_type', 'start_date')
    search_fields = ('job_title', 'employer_name', 'job_category')
    readonly_fields = ('document',)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('skill_name', 'skill_category', 'proficiency_level')
    list_filter = ('skill_category', 'proficiency_level')
    search_fields = ('skill_name', 'skill_category')
    readonly_fields = ('document',)


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ('milestone_type', 'issuer_name', 'date')
    list_filter = ('milestone_type', 'date')
    search_fields = ('issuer_name', 'milestone_summary')
    readonly_fields = ('document',)


@admin.register(CommunityContribution)
class CommunityContributionAdmin(admin.ModelAdmin):
    list_display = ('contribution_type', 'platform_name', 'date')
    list_filter = ('contribution_type', 'date')
    search_fields = ('platform_name',)
    readonly_fields = ('document',)


@admin.register(EvidenceFile)
class EvidenceFileAdmin(admin.ModelAdmin):
    list_display = ('document', 'file_type', 'file_size', 'uploaded_at')
    list_filter = ('file_type', 'uploaded_at')
    search_fields = ('document__internal_id', 'description')
    readonly_fields = ('id', 'uploaded_at', 'file_size')
