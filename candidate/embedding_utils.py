from typing import List, Dict
from google import genai
from django.conf import settings
from dotenv import load_dotenv
import os

# Initialize Gemini client
load_dotenv()

api_key = os.getenv("GEMINI_API")
client = genai.Client(api_key=api_key)

def parse_job_description(jd_text: str) -> Dict[str, str]:
    """
    Parse a job description into different aspects using Gemini.
    
    Args:
        jd_text (str): The full job description text
    
    Returns:
        Dict[str, str]: Dictionary containing different aspects of the job description
    """
    try:
        print(f"Parsing job description of length: {len(jd_text)}")
        prompt = f"""
        Parse the following job description into different aspects. Extract and organize the information into these categories:
        1. Required Skills and Technologies
        2. Experience Requirements
        3. Project Requirements
        4. Location and Work Arrangement
        5. General Profile Requirements

        Job Description:
        {jd_text}

        Provide the output in a structured format with clear sections.
        """

        print("Sending request to Gemini API for parsing")
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        print("Received response from Gemini API")
        
        # Parse the response into sections
        sections = {
            "skills": "",
            "experience": "",
            "projects": "",
            "location": "",
            "profile": ""
        }
        
        try:
            print("Attempting to parse response text")
            # Parse the text response into sections
            current_section = None
            for line in response.text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                if "Required Skills" in line or "Skills and Technologies" in line:
                    current_section = "skills"
                elif "Experience" in line:
                    current_section = "experience"
                elif "Project" in line:
                    current_section = "projects"
                elif "Location" in line or "Work Arrangement" in line:
                    current_section = "location"
                elif "Profile" in line or "General" in line:
                    current_section = "profile"
                elif current_section:
                    sections[current_section] += line + " "
            
            print("Successfully parsed response text")
        except Exception as e:
            print(f"Text parsing failed: {str(e)}")
            print("Using default sections")
        
        # Clean up the sections
        for key in sections:
            sections[key] = sections[key].strip()
            if not sections[key]:
                sections[key] = "No specific requirements mentioned"
        
        print(f"Final parsed sections: {list(sections.keys())}")
        return sections
    except Exception as e:
        print(f"Error parsing job description: {str(e)}")
        print(f"Full error details: {type(e).__name__}: {str(e)}")
        # Return default sections if parsing fails
        return {
            "skills": jd_text,
            "experience": jd_text,
            "projects": jd_text,
            "location": jd_text,
            "profile": jd_text
        }

def get_embedding(text: str, dimension: int = 1536) -> List[float]:
    """
    Get embedding for a text using Gemini API.
    
    Args:
        text (str): The text to generate embedding for
        dimension (int): Dimension of the embedding vector (default: 1536)
    
    Returns:
        List[float]: The embedding vector for the text
    """
    try:
        print(f"Getting embedding for text of length: {len(text)}")
        result = client.models.embed_content(
            model="gemini-embedding-exp-03-07",
            contents=text
        )
        print("Received embedding response")
        
        # Convert ContentEmbedding to list of floats
        embedding = result.embeddings[0]
        print(f"Embedding type: {type(embedding)}")
        
        # Extract the embedding values
        if hasattr(embedding, 'values'):
            print("Using embedding.values")
            values = embedding.values
        elif isinstance(embedding, list):
            print("Using embedding as list")
            values = embedding
        else:
            print("Converting embedding to list")
            values = [float(x) for x in embedding]
        
        # Ensure the embedding has the correct dimension
        if len(values) != dimension:
            print(f"Warning: Embedding dimension mismatch. Expected {dimension}, got {len(values)}")
            # Pad or truncate to match the expected dimension
            if len(values) < dimension:
                values.extend([0.0] * (dimension - len(values)))
            else:
                values = values[:dimension]
        
        return values
    except Exception as e:
        print(f"Error getting embedding: {str(e)}")
        print(f"Full error details: {type(e).__name__}: {str(e)}")
        return [0.0] * dimension
