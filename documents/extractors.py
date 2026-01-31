"""
Document Extraction Service
Extracts data from uploaded files (PDFs, images) to auto-populate document fields
"""
import re
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import io

# These will be available when packages are installed
try:
    import PyPDF2
    from PIL import Image
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
    
except ImportError:
    PyPDF2 = None
    Image = None
    pytesseract = None


class DocumentExtractor:
    """Extract data from uploaded document files"""
    
    def __init__(self):
        self.extraction_patterns = {
            'certificate': {
                'title': [
                    # Match "Responsive Web Design" followed by optional words ending in "Certification"
                    r'successfully completed the\s+([A-Za-z0-9\s\-&,]+?)\s+(?:Developer\s+)?(?:Certification|Certificate)',
                    r'(?:Certificate of|Certification in|Course[:\s]+)([A-Za-z0-9\s\-&,]+?)(?:\n|$|Issued)',
                    r'(?:has successfully completed|certifies that.*?completed)\s+(?:the\s+)?([A-Za-z0-9\s\-&,]+?)(?:\s+on|\s+Certification|\n)',
                ],
                'issuer': [
                    # Match common platform names at start or with specific context
                    r'^([A-Za-z]+(?:Camp|Academy|University|Institute|School|Code|Learn))',
                    r'(?:Executive Director|issued by),?\s+([A-Za-z0-9\s\-&\.]+?)(?:\.|$|\n)',
                    r'(?:Issued by[:\s]+|Issuer[:\s]+)([A-Za-z0-9\s\-&,\.]+?)(?:\n|$)',
                    r'(?:from|by)\s+([A-Z][A-Za-z\s&]+(?:University|Institute|Academy|Foundation|College|School|Company|Camp))',
                ],
                'date': [
                    # Match "on October 28, 2023" format
                    r'on\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
                    r'(?:Completed|Issued|Date)[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
                    r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                    r'([A-Z][a-z]+\s+\d{4})',
                ],
                'credential_type': [
                    r'\b(Certificate|Certification|Course|Bootcamp|Workshop|Award)\b',
                ]
            },
            'job_history': {
                'job_title': [
                    r'(?:Position|Title|Role)[:\s]+([A-Za-z0-9\s\-&,]+?)(?:\n|$)',
                    r'(?:as|as a|as an)\s+([A-Z][A-Za-z\s]+(?:Engineer|Developer|Manager|Analyst|Designer|Specialist))',
                ],
                'employer': [
                    r'(?:Company|Employer|Organization)[:\s]+([A-Za-z0-9\s\-&,\.]+?)(?:\n|$)',
                    r'(?:at|with)\s+([A-Z][A-Za-z\s&]+(?:Inc|LLC|Ltd|Corp|Company))',
                ],
                'start_date': [
                    r'(?:Start Date|From|Beginning)[:\s]+([A-Za-z]+\s+\d{4})',
                    r'(?:From|Since)\s+([A-Z][a-z]+\s+\d{4})',
                ],
                'employment_type': [
                    r'\b(Full-time|Part-time|Contract|Intern|Contributor|Full time|Part time)\b',
                ]
            }
        }
    
    def extract_from_file(self, file_obj, proof_type: str) -> Tuple[Dict[str, Any], str]:
        """
        Extract data from uploaded file
        
        Args:
            file_obj: Django UploadedFile object
            proof_type: Type of document (certificate, job_history, etc.)
            
        Returns:
            Tuple of (extracted_data dict, raw_text)
        """
        file_extension = file_obj.name.split('.')[-1].lower()
        
        try:
            if file_extension == 'pdf':
                text = self._extract_from_pdf(file_obj)
            elif file_extension in ['png', 'jpg', 'jpeg', 'gif', 'tiff']:
                text = self._extract_from_image(file_obj)
            else:
                return {}, "Unsupported file type"
            
            # Extract structured data based on proof type
            extracted_data = self._extract_structured_data(text, proof_type)
            
            return extracted_data, text
            
        except Exception as e:
            return {}, f"Error extracting data: {str(e)}"
    
    def _extract_from_pdf(self, file_obj) -> str:
        """Extract text from PDF file"""
        if PyPDF2 is None:
            raise ImportError("PyPDF2 is required for PDF extraction. Install with: pip install PyPDF2")
        
        text = ""
        try:
            # Reset file pointer
            file_obj.seek(0)
            
            # Read PDF
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_obj.read()))
            
            # Extract text from all pages
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
            
            return text.strip()
        except Exception as e:
            raise Exception(f"PDF extraction failed: {str(e)}")
    
    def _extract_from_image(self, file_obj) -> str:
        """Extract text from image file using OCR"""
        if Image is None or pytesseract is None:
            raise ImportError(
                "PIL and pytesseract are required for image extraction. "
                "Install with: pip install Pillow pytesseract"
            )
        
        try:
            # Reset file pointer
            file_obj.seek(0)
            
            # Open image
            image = Image.open(file_obj)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Extract text using OCR
            text = pytesseract.image_to_string(image)
            
            return text.strip()
        except Exception as e:
            raise Exception(f"Image extraction failed: {str(e)}")
    
    def _extract_structured_data(self, text: str, proof_type: str) -> Dict[str, Any]:
        """Extract structured data from text based on proof type"""
        if proof_type not in self.extraction_patterns:
            return {}
        
        patterns = self.extraction_patterns[proof_type]
        extracted = {}
        
        for field, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(1).strip()
                    
                    # Clean up the value
                    value = self._clean_extracted_value(value, field)
                    
                    if value:
                        extracted[field] = value
                        break  # Use first successful match
        
        # Post-process extracted data
        extracted = self._post_process_data(extracted, proof_type)
        
        return extracted
    
    def _clean_extracted_value(self, value: str, field: str) -> str:
        """Clean up extracted values"""
        # Remove extra whitespace
        value = ' '.join(value.split())
        
        # Remove trailing punctuation
        value = value.rstrip('.,;:')
        
        # Specific cleaning based on field type
        if 'date' in field:
            value = self._normalize_date(value)
        elif field == 'credential_type':
            value = value.capitalize()
        elif field == 'employment_type':
            value = value.lower().replace(' ', '-')
        
        return value
    
    def _normalize_date(self, date_str: str) -> str:
        """Normalize date to YYYY-MM format"""
        date_str = date_str.strip()
        
        # Try to parse various date formats
        formats_to_try = [
            '%B %d, %Y',  # October 28, 2023
            '%b %d, %Y',  # Oct 28, 2023
            '%B %d %Y',   # October 28 2023 (no comma)
            '%b %d %Y',   # Oct 28 2023
            '%B %Y',      # October 2023
            '%b %Y',      # Oct 2023
            '%m/%d/%Y',   # 10/28/2023
            '%m-%d-%Y',   # 10-28-2023
            '%d/%m/%Y',   # 28/10/2023
            '%Y-%m-%d',   # 2023-10-28
        ]
        
        for fmt in formats_to_try:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m')
            except ValueError:
                continue
        
        # If no format worked, try to extract year and month
        year_match = re.search(r'\b(20\d{2})\b', date_str)
        month_match = re.search(r'\b(0?[1-9]|1[0-2])\b', date_str)
        
        if year_match and month_match:
            year = year_match.group(1)
            month = month_match.group(1).zfill(2)
            return f"{year}-{month}"
        
        # Try month name extraction
        month_names = {
            'january': '01', 'february': '02', 'march': '03', 'april': '04',
            'may': '05', 'june': '06', 'july': '07', 'august': '08',
            'september': '09', 'october': '10', 'november': '11', 'december': '12',
            'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
            'jun': '06', 'jul': '07', 'aug': '08', 'sep': '09',
            'oct': '10', 'nov': '11', 'dec': '12'
        }
        
        for month_name, month_num in month_names.items():
            if month_name in date_str.lower() and year_match:
                return f"{year_match.group(1)}-{month_num}"
        
        return date_str  # Return as-is if can't parse
    
    def _post_process_data(self, data: Dict[str, Any], proof_type: str) -> Dict[str, Any]:
        """Post-process extracted data"""
        processed = {}
        
        if proof_type == 'certificate':
            # Map extracted fields to model fields
            if 'title' in data:
                processed['certificate_title'] = data['title']
            if 'issuer' in data:
                processed['issuer_name'] = data['issuer']
            if 'date' in data:
                processed['completion_date'] = data['date']
            if 'credential_type' in data:
                # Normalize to allowed values
                cred_type = data['credential_type'].capitalize()
                if cred_type in ['Certificate', 'Certification']:
                    cred_type = 'Course'  # Default mapping
                if cred_type in ['Course', 'Bootcamp', 'Workshop', 'Award']:
                    processed['credential_type'] = cred_type
        
        elif proof_type == 'job_history':
            if 'job_title' in data:
                processed['job_title'] = data['job_title']
            if 'employer' in data:
                processed['employer_name'] = data['employer']
            if 'start_date' in data:
                processed['start_date'] = data['start_date']
            if 'employment_type' in data:
                emp_type = data['employment_type'].lower().replace(' ', '-')
                if emp_type in ['full-time', 'part-time', 'intern', 'contributor', 'contract']:
                    processed['employment_type'] = emp_type
        
        return processed
    
    def suggest_missing_fields(self, extracted_data: Dict[str, Any], 
                              proof_type: str) -> Dict[str, str]:
        """Suggest values for missing required fields"""
        suggestions = {}
        
        required_fields = {
            'certificate': {
                'certificate_title': 'Professional Certificate',
                'program_category': 'Professional Development',
            },
            'job_history': {
                'job_category': 'General',
            }
        }
        
        if proof_type in required_fields:
            for field, default_value in required_fields[proof_type].items():
                if field not in extracted_data:
                    suggestions[field] = default_value
        
        return suggestions
    
    def get_extraction_confidence(self, extracted_data: Dict[str, Any], 
                                  proof_type: str) -> Dict[str, Any]:
        """Calculate confidence scores for extracted data"""
        confidence = {
            'overall': 0.0,
            'fields': {}
        }
        
        required_fields = {
            'certificate': ['certificate_title', 'issuer_name', 'completion_date'],
            'job_history': ['job_title', 'employer_name', 'start_date'],
        }
        
        if proof_type not in required_fields:
            return confidence
        
        total_required = len(required_fields[proof_type])
        found_required = sum(
            1 for field in required_fields[proof_type] 
            if field in extracted_data and extracted_data[field]
        )
        
        confidence['overall'] = (found_required / total_required) * 100
        
        # Individual field confidence
        for field, value in extracted_data.items():
            if value and len(value) > 3:
                confidence['fields'][field] = 'high'
            elif value:
                confidence['fields'][field] = 'low'
        
        return confidence


def extract_and_create_document(file_obj, proof_type: str, 
                                user_provided_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Convenience function to extract data from file and merge with user data
    
    Args:
        file_obj: Uploaded file
        proof_type: Type of document
        user_provided_data: Additional data provided by user
        
    Returns:
        Dictionary with merged data and metadata
    """
    extractor = DocumentExtractor()
    extracted_data, raw_text = extractor.extract_from_file(file_obj, proof_type)
    
    # Merge with user-provided data (user data takes precedence)
    merged_data = {**extracted_data}
    if user_provided_data:
        merged_data.update(user_provided_data)
    
    # Add suggestions for missing fields
    suggestions = extractor.suggest_missing_fields(merged_data, proof_type)
    
    # Calculate confidence
    confidence = extractor.get_extraction_confidence(extracted_data, proof_type)
    
    return {
        'extracted_data': extracted_data,
        'merged_data': merged_data,
        'suggestions': suggestions,
        'confidence': confidence,
        'raw_text': raw_text[:500] if raw_text else None,  # First 500 chars
    }
