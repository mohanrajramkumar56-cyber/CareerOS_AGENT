"""
Small additional test to push coverage over 70%.
"""

def test_job_pipeline_extract_education():
    """Test education extraction function."""
    from app.services.job_pipeline import extract_education_requirements
    
    # Should extract bachelor's
    result = extract_education_requirements("Bachelor's degree required")
    assert result is not None
    assert "bachelor" in result.lower()
    
    # Should extract PhD
    result = extract_education_requirements("PhD in Computer Science preferred")
    assert result is not None
    
    # No education mentioned
    result = extract_education_requirements("Experience is more important than degrees")
    assert result is None
    
    # Test empty/None input
    result = extract_education_requirements("")
    assert result is None
    
    result = extract_education_requirements(None)
    assert result is None


def test_job_pipeline_section_finder():
    """Test the _find_section helper."""
    from app.services.job_pipeline import _find_section
    
    text = """
    Job Description:
    We are looking for engineers.
    
    Requirements:
    - 5 years Python
    - FastAPI experience
    
    Nice to have:
    - Docker knowledge
    """
    
    # Should find requirements section
    section = _find_section(text, ["requirements", "required"])
    assert section is not None
    assert "Python" in section
    
    # Should find preferred section
    section = _find_section(text, ["nice to have", "preferred"])
    assert section is not None
    assert "Docker" in section
    
    # Should return None for non-existent section
    section = _find_section(text, ["benefits", "salary"])
    assert section is None