def extract_text_from_response(response: dict) -> dict:
    """Extract text lines from Textract response"""
    lines = []
    for block in response.get("Blocks", []):
        if block.get("BlockType") == "LINE":
            text = block.get("Text")
            if text:
                lines.append(text)
    
    full_text = "\n".join(lines)
    
    return {
        'num_lines': len(lines),
        'preview': '\n'.join(lines[:15]),
        'full_text': full_text
    }