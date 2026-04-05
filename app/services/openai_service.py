import json
import os
from openai import OpenAI
from app.models.schemas import ParsedSyllabus

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def parse_syllabus_with_openai(text: str) -> ParsedSyllabus:
    """
    Use OpenAI to extract course + assignments from raw syllabus text.
    Returns a ParsedSyllabus Pydantic model.
    """

    system_prompt = """You are an expert at parsing academic syllabi. Extract structured information from the provided syllabus text.

    Extract the following information:
    1. Course information: course code, course name, instructor, semester, year, credits
    2. Assignments: name, due date, weight/percentage, description
    3. Reminders: important dates, deadlines, exam dates, etc.

    IMPORTANT DATE FORMATTING RULES:
    - Dates MUST be in ISO format: YYYY-MM-DD (e.g., "2025-10-15")
    - If a date is not available or cannot be determined, use null (NOT a description like "Final Deliverables")
    - If you see text like "Final Deliverables", "Week of...", or date ranges, use null for the date field
    - Only extract actual calendar dates in YYYY-MM-DD format
    - If the year is not specified, infer it from the course year/semester context

    Return the data as a JSON object matching this structure:
    {
        "course": {
            "course_code": "CS 686",
            "course_name": "Cloud Computing",
            "instructor": "Dr. Smith",
            "semester": "Fall",
            "year": "2025",
            "credits": 3.0
        },
        "assignments": [
            {
                "name": "Project 1",
                "due_date": "2025-10-15",
                "weight": 25.0,
                "description": "Build a cloud application"
            }
        ],
        "reminders": [
            {
                "title": "Midterm Exam",
                "date": "2025-11-01",
                "description": "Midterm exam covering chapters 1-5"
            }
        ]
    }

    If information is not available, use null for that field. Return ONLY valid JSON, no additional text."""
        
    user_prompt = f"""Parse the following syllabus text and extract structured information:

                    {text}

                    Return the structured data as JSON."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},  # Force JSON response
            temperature=0.3 # Lower temperature for more consistent parsing
        )

        # Extract JSON from response
        content = response.choices[0].message.content
        parsed_data = json.loads(content)

        # Add raw text to the parsed data
        parsed_data['raw_text'] = text

        # Validate with Pydantic model
        parsed_syllabus = ParsedSyllabus.model_validate(parsed_data)

        # Print parsed result
        print("\n" + "=" * 60)
        print("📋 PARSED RESULT:")
        print("=" * 60)
        print(json.dumps(parsed_data, indent=2))
        print("=" * 60 + "\n")

        # Return Pydantic model
        return parsed_syllabus

    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse OpenAI response as JSON: {str(e)}")
    except Exception as e:
        raise ValueError(f"OpenAI API error: {str(e)}")

        


