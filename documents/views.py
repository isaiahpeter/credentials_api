"""
Enhanced API Views with Document Extraction
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Count, Q
from .models import Document, Certificate, JobHistory, Skill, Milestone, CommunityContribution
from .serializers import (
    DocumentSerializer, DocumentCreateSerializer, 
    BatchProcessSerializer, DocumentStatsSerializer
)
from .services import DocumentProcessorService
from .extractors import DocumentExtractor, extract_and_create_document


class DocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing credential documents with extraction support
    """
    queryset = Document.objects.all().select_related(
        'certificate', 'job_history', 'skill', 'milestone', 'community_contribution'
    ).prefetch_related('evidence_files')
    serializer_class = DocumentSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    
    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = super().get_queryset()
        
        proof_type = self.request.query_params.get('proof_type')
        if proof_type:
            queryset = queryset.filter(proof_type=proof_type)
        
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Create a new document"""
        serializer = DocumentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        proof_type = serializer.validated_data['proof_type']
        data = serializer.validated_data['data']
        user_id = serializer.validated_data.get('user_id') or request.query_params.get('user_id')
        evidence_files = request.FILES.getlist('evidence_files', [])
        
        processor = DocumentProcessorService()
        document, errors = processor.process_document(
            proof_type, 
            data, 
            user_id,
            evidence_files
        )
        
        if document:
            response_serializer = DocumentSerializer(document, context={'request': request})
            return Response(
                {
                    'status': 'success',
                    'message': 'Document created successfully',
                    'data': response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(
                {
                    'status': 'error',
                    'message': 'Failed to create document',
                    'errors': errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def extract_and_create(self, request):
        """
        Extract data from uploaded file and create document
        
        This endpoint accepts a file upload and automatically extracts
        data using OCR/PDF parsing, then creates the document.
        
        Required fields:
        - file: The document file (PDF or image)
        - proof_type: Type of document (certificate, job_history, etc.)
        
        Optional fields:
        - Any additional fields to override extracted data
        - user_id: User identifier
        """
        if 'file' not in request.FILES:
            return Response(
                {
                    'status': 'error',
                    'message': 'No file provided'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file_obj = request.FILES['file']
        proof_type = request.data.get('proof_type')
        
        if not proof_type:
            return Response(
                {
                    'status': 'error',
                    'message': 'proof_type is required'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Extract data from file
            extractor = DocumentExtractor()
            extracted_data, raw_text = extractor.extract_from_file(file_obj, proof_type)
            
            # Get user-provided overrides
            user_data = {}
            for key, value in request.data.items():
                if key not in ['file', 'proof_type', 'user_id']:
                    user_data[key] = value
            
            # Merge extracted and user data
            merged_data = {**extracted_data, **user_data}
            
            # Get suggestions for missing fields
            suggestions = extractor.suggest_missing_fields(merged_data, proof_type)
            merged_data.update(suggestions)
            
            # Calculate confidence
            confidence = extractor.get_extraction_confidence(extracted_data, proof_type)
            
            # Check if we have minimum required fields
            if confidence['overall'] < 50:
                return Response(
                    {
                        'status': 'partial',
                        'message': 'Low confidence extraction. Please review and provide missing data.',
                        'extracted_data': extracted_data,
                        'suggestions': suggestions,
                        'confidence': confidence,
                        'raw_text_sample': raw_text[:300] if raw_text else None
                    },
                    status=status.HTTP_200_OK
                )
            
            # Create document with extracted data
            user_id = request.data.get('user_id')
            processor = DocumentProcessorService()
            document, errors = processor.process_document(
                proof_type,
                merged_data,
                user_id,
                [file_obj]  # Save the original file as evidence
            )
            
            if document:
                response_serializer = DocumentSerializer(document, context={'request': request})
                return Response(
                    {
                        'status': 'success',
                        'message': 'Document extracted and created successfully',
                        'data': response_serializer.data,
                        'extraction_info': {
                            'extracted_fields': list(extracted_data.keys()),
                            'confidence': confidence,
                            'suggested_fields': list(suggestions.keys())
                        }
                    },
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    {
                        'status': 'error',
                        'message': 'Failed to create document',
                        'errors': errors,
                        'extracted_data': extracted_data
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        except ImportError as e:
            return Response(
                {
                    'status': 'error',
                    'message': 'Document extraction not available. Required libraries not installed.',
                    'details': str(e)
                },
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        except Exception as e:
            return Response(
                {
                    'status': 'error',
                    'message': 'Extraction failed',
                    'details': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def extract_preview(self, request):
        """
        Preview extracted data without creating document
        
        This endpoint extracts data from a file and returns the results
        without saving to database. Useful for showing users what was
        extracted before they confirm.
        """
        if 'file' not in request.FILES:
            return Response(
                {
                    'status': 'error',
                    'message': 'No file provided'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file_obj = request.FILES['file']
        proof_type = request.data.get('proof_type')
        
        if not proof_type:
            return Response(
                {
                    'status': 'error',
                    'message': 'proof_type is required'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get user-provided data for merging
            user_data = {}
            for key, value in request.data.items():
                if key not in ['file', 'proof_type']:
                    user_data[key] = value
            
            # Extract and merge
            result = extract_and_create_document(file_obj, proof_type, user_data)
            
            return Response(
                {
                    'status': 'success',
                    'message': 'Data extracted successfully',
                    'extracted_data': result['extracted_data'],
                    'merged_data': result['merged_data'],
                    'suggestions': result['suggestions'],
                    'confidence': result['confidence'],
                    'raw_text_sample': result['raw_text']
                },
                status=status.HTTP_200_OK
            )
        
        except ImportError as e:
            return Response(
                {
                    'status': 'error',
                    'message': 'Document extraction not available',
                    'details': str(e)
                },
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        except Exception as e:
            return Response(
                {
                    'status': 'error',
                    'message': 'Extraction failed',
                    'details': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def batch_create(self, request):
        """Create multiple documents in batch"""
        serializer = BatchProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        documents_data = []
        for doc in serializer.validated_data['documents']:
            documents_data.append({
                'proof_type': doc['proof_type'],
                'data': doc['data'],
                'evidence_files': doc.get('evidence_files', [])
            })
        
        user_id = serializer.validated_data.get('user_id') or request.query_params.get('user_id')
        
        processor = DocumentProcessorService()
        results = processor.process_batch(documents_data, user_id)
        
        return Response(
            {
                'status': 'success',
                'message': f"Processed {results['statistics']['total']} documents",
                'data': results
            },
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get statistics about documents"""
        user_id = request.query_params.get('user_id')
        queryset = Document.objects.all()
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        by_type = queryset.values('proof_type').annotate(
            count=Count('id')
        ).order_by('proof_type')
        
        by_status = queryset.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        recent = queryset.select_related(
            'certificate', 'job_history', 'skill', 'milestone', 'community_contribution'
        ).prefetch_related('evidence_files')[:10]
        
        stats_data = {
            'total_documents': queryset.count(),
            'by_type': {item['proof_type']: item['count'] for item in by_type},
            'by_status': {item['status']: item['count'] for item in by_status},
            'recent_documents': recent
        }
        
        serializer = DocumentStatsSerializer(stats_data, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Mark a document as verified"""
        document = self.get_object()
        document.status = 'verified'
        document.save()
        
        serializer = self.get_serializer(document)
        return Response(
            {
                'status': 'success',
                'message': 'Document verified successfully',
                'data': serializer.data
            }
        )
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Mark a document as rejected"""
        document = self.get_object()
        document.status = 'rejected'
        document.save()
        
        serializer = self.get_serializer(document)
        return Response(
            {
                'status': 'success',
                'message': 'Document rejected',
                'data': serializer.data
            }
        )
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get documents grouped by type"""
        proof_type = request.query_params.get('type')
        user_id = request.query_params.get('user_id')
        
        if not proof_type:
            return Response(
                {
                    'status': 'error',
                    'message': 'type parameter is required'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = Document.objects.filter(proof_type=proof_type)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        queryset = queryset.select_related(
            'certificate', 'job_history', 'skill', 'milestone', 'community_contribution'
        ).prefetch_related('evidence_files')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CertificateViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing certificates"""
    queryset = Document.objects.filter(proof_type='certificate')
    serializer_class = DocumentSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(document__user_id=user_id)
        return queryset


class JobHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing job history"""
    queryset = JobHistory.objects.all().select_related('document')
    serializer_class = DocumentSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(document__user_id=user_id)
        return queryset


class SkillViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing skills"""
    queryset = Skill.objects.all().select_related('document')
    serializer_class = DocumentSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(document__user_id=user_id)
        return queryset
