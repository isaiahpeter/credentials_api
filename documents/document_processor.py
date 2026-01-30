"""
Document Processing Service - Integration with Django models
"""
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Any, Tuple
from .models import (
    Document, Certificate, JobHistory, Skill,
    Milestone, CommunityContribution, EvidenceFile
)


class DocumentProcessorService:
    """Service for processing credential documents"""
    
    @staticmethod
    def generate_hash(data: Dict[str, Any]) -> str:
        """Generate validation hash from extracted data"""
        sorted_data = json.dumps(data, sort_keys=True)
        return hashlib.sha256(sorted_data.encode()).hexdigest()
    
    @staticmethod
    def generate_internal_id(proof_type: str, timestamp: datetime = None) -> str:
        """Generate internal ID for tracking"""
        if timestamp is None:
            timestamp = datetime.now()
        ts_str = timestamp.strftime("%Y%m%d%H%M%S%f")
        return f"{proof_type}_{ts_str}"
    
    def process_certificate(self, data: Dict[str, Any], user_id: str = None) -> Document:
        """Process certificate data and create database records"""
        # Extract only allowed fields
        onchain_data = {
            'certificate_title': data['certificate_title'],
            'issuer_name': data['issuer_name'],
            'completion_date': data['completion_date'],
            'credential_type': data['credential_type'],
            'program_category': data['program_category']
        }
        
        # Generate hash and ID
        validation_hash = self.generate_hash(onchain_data)
        internal_id = self.generate_internal_id('certificate')
        
        # Create Document
        document = Document.objects.create(
            proof_type='certificate',
            internal_id=internal_id,
            validation_hash=validation_hash,
            onchain_data=onchain_data,
            user_id=user_id,
            status='pending'
        )
        
        # Create Certificate
        Certificate.objects.create(
            document=document,
            **onchain_data
        )
        
        return document
    
    def process_job_history(self, data: Dict[str, Any], user_id: str = None) -> Document:
        """Process job history data and create database records"""
        onchain_data = {
            'job_title': data['job_title'],
            'employer_name': data['employer_name'],
            'employment_type': data['employment_type'],
            'start_date': data['start_date'],
            'end_date': data.get('end_date'),
            'job_category': data['job_category']
        }
        
        validation_hash = self.generate_hash(onchain_data)
        internal_id = self.generate_internal_id('job_history')
        
        document = Document.objects.create(
            proof_type='job_history',
            internal_id=internal_id,
            validation_hash=validation_hash,
            onchain_data=onchain_data,
            user_id=user_id,
            status='pending'
        )
        
        JobHistory.objects.create(
            document=document,
            **onchain_data
        )
        
        return document
    
    def process_skill(self, data: Dict[str, Any], user_id: str = None) -> Document:
        """Process skill data and create database records"""
        onchain_data = {
            'skill_name': data['skill_name'],
            'skill_category': data['skill_category'],
            'proficiency_level': data.get('proficiency_level')
        }
        
        validation_hash = self.generate_hash(onchain_data)
        internal_id = self.generate_internal_id('skill')
        
        document = Document.objects.create(
            proof_type='skill',
            internal_id=internal_id,
            validation_hash=validation_hash,
            onchain_data=onchain_data,
            user_id=user_id,
            status='pending'
        )
        
        Skill.objects.create(
            document=document,
            **onchain_data
        )
        
        return document
    
    def process_milestone(self, data: Dict[str, Any], user_id: str = None) -> Document:
        """Process milestone data and create database records"""
        onchain_data = {
            'milestone_type': data['milestone_type'],
            'issuer_name': data['issuer_name'],
            'date': data['date'],
            'milestone_summary': data['milestone_summary']
        }
        
        validation_hash = self.generate_hash(onchain_data)
        internal_id = self.generate_internal_id('milestone')
        
        document = Document.objects.create(
            proof_type='milestone',
            internal_id=internal_id,
            validation_hash=validation_hash,
            onchain_data=onchain_data,
            user_id=user_id,
            status='pending'
        )
        
        Milestone.objects.create(
            document=document,
            **onchain_data
        )
        
        return document
    
    def process_community_contribution(self, data: Dict[str, Any], user_id: str = None) -> Document:
        """Process community contribution data and create database records"""
        onchain_data = {
            'contribution_type': data['contribution_type'],
            'platform_name': data['platform_name'],
            'date': data['date']
        }
        
        validation_hash = self.generate_hash(onchain_data)
        internal_id = self.generate_internal_id('community')
        
        document = Document.objects.create(
            proof_type='community',
            internal_id=internal_id,
            validation_hash=validation_hash,
            onchain_data=onchain_data,
            user_id=user_id,
            status='pending'
        )
        
        CommunityContribution.objects.create(
            document=document,
            **onchain_data
        )
        
        return document
    
    def process_document(self, proof_type: str, data: Dict[str, Any], 
                        user_id: str = None, evidence_files: List = None) -> Tuple[Document, List[str]]:
        """
        Process a document of any type
        
        Returns:
            Tuple of (Document object, list of error messages)
        """
        errors = []
        document = None
        
        try:
            # Process based on type
            if proof_type == 'certificate':
                document = self.process_certificate(data, user_id)
            elif proof_type == 'job_history':
                document = self.process_job_history(data, user_id)
            elif proof_type == 'skill':
                document = self.process_skill(data, user_id)
            elif proof_type == 'milestone':
                document = self.process_milestone(data, user_id)
            elif proof_type == 'community':
                document = self.process_community_contribution(data, user_id)
            else:
                errors.append(f"Unknown proof type: {proof_type}")
                return None, errors
            
            # Process evidence files if provided
            if document and evidence_files:
                for file_obj in evidence_files:
                    try:
                        EvidenceFile.objects.create(
                            document=document,
                            file=file_obj,
                            file_type=file_obj.content_type or 'unknown',
                            description=f"Evidence for {proof_type}"
                        )
                    except Exception as e:
                        errors.append(f"Error uploading file {file_obj.name}: {str(e)}")
            
        except Exception as e:
            errors.append(str(e))
            if document:
                document.delete()
            document = None
        
        return document, errors
    
    def process_batch(self, documents_data: List[Dict[str, Any]], 
                     user_id: str = None) -> Dict[str, Any]:
        """
        Process multiple documents in batch
        
        Returns:
            Dictionary with results and statistics
        """
        results = []
        stats = {
            'total': len(documents_data),
            'successful': 0,
            'failed': 0
        }
        
        for idx, doc_data in enumerate(documents_data):
            proof_type = doc_data.get('proof_type')
            data = doc_data.get('data', {})
            evidence_files = doc_data.get('evidence_files', [])
            
            document, errors = self.process_document(
                proof_type, 
                data, 
                user_id,
                evidence_files
            )
            
            if document:
                stats['successful'] += 1
                results.append({
                    'index': idx,
                    'proof_type': proof_type,
                    'status': 'success',
                    'document_id': str(document.id),
                    'internal_id': document.internal_id
                })
            else:
                stats['failed'] += 1
                results.append({
                    'index': idx,
                    'proof_type': proof_type,
                    'status': 'failed',
                    'errors': errors
                })
        
        return {
            'results': results,
            'statistics': stats
        }
