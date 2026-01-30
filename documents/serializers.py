"""
Serializers for REST API
"""
from rest_framework import serializers
from .models import (
    Document, Certificate, JobHistory, Skill, 
    Milestone, CommunityContribution, EvidenceFile
)


class EvidenceFileSerializer(serializers.ModelSerializer):
    """Serializer for evidence files"""
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = EvidenceFile
        fields = ['id', 'file', 'file_url', 'file_type', 'description', 
                 'uploaded_at', 'file_size']
        read_only_fields = ['id', 'uploaded_at', 'file_size']
    
    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class CertificateSerializer(serializers.ModelSerializer):
    """Serializer for certificates"""
    class Meta:
        model = Certificate
        fields = ['certificate_title', 'issuer_name', 'completion_date',
                 'credential_type', 'program_category']


class JobHistorySerializer(serializers.ModelSerializer):
    """Serializer for job history"""
    class Meta:
        model = JobHistory
        fields = ['job_title', 'employer_name', 'employment_type',
                 'start_date', 'end_date', 'job_category']


class SkillSerializer(serializers.ModelSerializer):
    """Serializer for skills"""
    class Meta:
        model = Skill
        fields = ['skill_name', 'skill_category', 'proficiency_level']


class MilestoneSerializer(serializers.ModelSerializer):
    """Serializer for milestones"""
    class Meta:
        model = Milestone
        fields = ['milestone_type', 'issuer_name', 'date', 'milestone_summary']


class CommunityContributionSerializer(serializers.ModelSerializer):
    """Serializer for community contributions"""
    class Meta:
        model = CommunityContribution
        fields = ['contribution_type', 'platform_name', 'date']


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for documents with related data"""
    certificate = CertificateSerializer(read_only=True)
    job_history = JobHistorySerializer(read_only=True)
    skill = SkillSerializer(read_only=True)
    milestone = MilestoneSerializer(read_only=True)
    community_contribution = CommunityContributionSerializer(read_only=True)
    evidence_files = EvidenceFileSerializer(many=True, read_only=True)
    
    class Meta:
        model = Document
        fields = ['id', 'proof_type', 'internal_id', 'validation_hash',
                 'created_at', 'updated_at', 'onchain_data', 'user_id',
                 'status', 'certificate', 'job_history', 'skill',
                 'milestone', 'community_contribution', 'evidence_files']
        read_only_fields = ['id', 'internal_id', 'validation_hash', 
                           'created_at', 'updated_at']


class DocumentCreateSerializer(serializers.Serializer):
    """Serializer for creating documents"""
    proof_type = serializers.ChoiceField(choices=[
        'certificate', 'job_history', 'skill', 'milestone', 'community'
    ])
    data = serializers.JSONField()
    user_id = serializers.CharField(required=False, allow_blank=True)
    evidence_files = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        allow_empty=True
    )
    
    def validate_data(self, value):
        """Validate that required fields are present based on proof_type"""
        proof_type = self.initial_data.get('proof_type')
        
        required_fields = {
            'certificate': ['certificate_title', 'issuer_name', 'completion_date',
                          'credential_type', 'program_category'],
            'job_history': ['job_title', 'employer_name', 'employment_type',
                          'start_date', 'job_category'],
            'skill': ['skill_name', 'skill_category'],
            'milestone': ['milestone_type', 'issuer_name', 'date', 'milestone_summary'],
            'community': ['contribution_type', 'platform_name', 'date']
        }
        
        if proof_type in required_fields:
            for field in required_fields[proof_type]:
                if field not in value or not value[field]:
                    raise serializers.ValidationError(
                        f"Missing required field: {field}"
                    )
        
        # Validate date formats
        date_fields = ['completion_date', 'start_date', 'end_date', 'date']
        for field in date_fields:
            if field in value and value[field]:
                date_value = value[field]
                try:
                    parts = date_value.split('-')
                    if len(parts) != 2 or len(parts[0]) != 4 or len(parts[1]) != 2:
                        raise serializers.ValidationError(
                            f"{field} must be in YYYY-MM format"
                        )
                    # Validate month is between 1-12
                    month = int(parts[1])
                    if month < 1 or month > 12:
                        raise serializers.ValidationError(
                            f"{field} has invalid month"
                        )
                except (ValueError, IndexError):
                    raise serializers.ValidationError(
                        f"Invalid {field} format. Use YYYY-MM"
                    )
        
        # Check for forbidden fields
        forbidden_fields = {
            'certificate': ['full_name', 'serial_number', 'email', 'phone',
                          'score', 'grade', 'instructor_names'],
            'job_history': ['department', 'manager_names', 'offer_letter_number',
                          'salary', 'compensation'],
            'skill': [],
            'milestone': ['performance_review', 'salary_info'],
            'community': []
        }
        
        if proof_type in forbidden_fields:
            for field in forbidden_fields[proof_type]:
                if field in value:
                    raise serializers.ValidationError(
                        f"Forbidden field detected: {field}. This information cannot be stored."
                    )
        
        return value


class BatchProcessSerializer(serializers.Serializer):
    """Serializer for batch processing"""
    documents = serializers.ListField(
        child=DocumentCreateSerializer()
    )
    user_id = serializers.CharField(required=False, allow_blank=True)


class DocumentStatsSerializer(serializers.Serializer):
    """Serializer for statistics response"""
    total_documents = serializers.IntegerField()
    by_type = serializers.DictField()
    by_status = serializers.DictField()
    recent_documents = DocumentSerializer(many=True)
