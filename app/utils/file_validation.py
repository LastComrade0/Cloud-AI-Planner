def validate_file_format(content: bytes, content_type: str) -> bool:
    """Validate file format by checking magic bytes"""
    if not content or len(content) < 4:
        return False
    
    # Check PDF
    if content_type == "application/pdf":
        return content[:4] == b'%PDF'
    
    # Check JPEG
    if content_type in ("image/jpeg", "image/jpg"):
        return content[:2] == b'\xff\xd8'
    
    # Check PNG
    if content_type == "image/png":
        return content[:8] == b'\x89PNG\r\n\x1a\n'
    
    # Check TIFF
    if content_type == "image/tiff":
        return content[:4] in (b'II*\x00', b'MM\x00*')
    
    return True  # If we can't validate, let Textract handle it


def check_pdf_requirements(content: bytes) -> tuple[bool, str]:
    """Check if PDF meets Textract requirements for DetectDocumentText"""
    # Check size (10 MB limit for synchronous operations)
    size_mb = len(content) / (1024 * 1024)
    if size_mb > 10:
        return False, f"PDF size ({size_mb:.2f} MB) exceeds 10 MB limit for synchronous operations"
    
    # Try to check page count (basic check)
    # Count occurrences of /Type/Page in the PDF
    try:
        content_str = content.decode('latin-1', errors='ignore')
        # This is a rough check - count page objects
        page_count = content_str.count('/Type/Page') + content_str.count('/Type /Page')
        if page_count > 1:
            return False, f"PDF appears to have {page_count} pages. DetectDocumentText only supports single-page PDFs. Use StartDocumentTextDetection for multi-page PDFs."
    except:
        pass  # If we can't check, let Textract handle it
    
    return True, ""