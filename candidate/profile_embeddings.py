import os
from typing import List, Dict, Any
import numpy as np
import faiss
from django.conf import settings
from .models import Candidate, Project, WorkExperience, Education
from .embedding_utils import get_embedding, parse_job_description

class ProfileEmbeddingManager:
    def __init__(self):
        # Initialize FAISS index for 1536-dimensional vectors with cosine similarity
        self.dimension = 1536
        self.index = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine similarity
        self.candidate_emails = []  # Store candidate emails in the same order as vectors
        self.index_path = "candidate_embeddings"
        
        # Weights for different aspects of the profile
        self.weights = {
            "profile": 0.3,
            "skills": 0.3,
            "experience": 0.2,
            "projects": 0.1,
            "location": 0.1
        }
        
        # Try to load existing index if it exists
        try:
            self.load_index(self.index_path)
        except Exception as e:
            print(f"No existing index found or error loading index: {str(e)}")
            # Initialize empty index
            self.index = faiss.IndexFlatIP(self.dimension)
            self.candidate_emails = []

    def _prepare_profile_text(self, candidate: Candidate) -> Dict[str, str]:
        """Prepare text for different sections of the profile."""
        # Basic profile information
        profile_text = f"""
        Name: {candidate.name}
        Current Role: {candidate.current_job_title or 'Not specified'}
        Company: {candidate.current_company or 'Not specified'}
        Experience: {candidate.experience or 0} years
        Skills: {candidate.skills or 'Not specified'}
        """

        # Skills section
        skills_text = candidate.skills or "No skills specified"

        # Experience summary
        work_experiences = WorkExperience.objects.filter(candidate=candidate)
        experience_text = "\n".join([
            f"Role: {exp.role_designation} at {exp.company_name} "
            f"({exp.start_date} to {exp.end_date or 'Present'})"
            for exp in work_experiences
        ]) or "No work experience specified"

        # Projects summary
        projects = Project.objects.filter(candidate=candidate)
        projects_text = "\n".join([
            f"Project: {proj.title}\n"
            f"Description: {proj.description}\n"
            f"Tech Stack: {proj.tech_stack}"
            for proj in projects
        ]) or "No projects specified"

        # Location preferences
        location_text = f"""
        Preferred Locations: {candidate.preferred_locations or 'Not specified'}
        Willing to Relocate: {'Yes' if candidate.willingness_to_relocate else 'No'}
        """

        return {
            "profile": profile_text,
            "skills": skills_text,
            "experience": experience_text,
            "projects": projects_text,
            "location": location_text
        }

    def generate_embeddings(self, candidate: Candidate) -> Dict[str, List[float]]:
        """Generate embeddings for all sections of a candidate's profile."""
        texts = self._prepare_profile_text(candidate)
        embeddings = {
            "profile_embedding": get_embedding(texts["profile"]),
            "skills_embedding": get_embedding(texts["skills"]),
            "experience_embedding": get_embedding(texts["experience"]),
            "projects_embedding": get_embedding(texts["projects"]),
            "location_embedding": get_embedding(texts["location"])
        }
        
        return embeddings

    def add_to_index(self, candidate: Candidate) -> None:
        """Add a candidate's profile to the FAISS index."""
        try:
            embeddings = self.generate_embeddings(candidate)
            
            # Normalize and add all embeddings to index
            for aspect, embedding in embeddings.items():
                # Normalize the embedding vector
                normalized_vector = self._normalize_vector(embedding)
                vector = np.array([normalized_vector], dtype=np.float32)
                self.index.add(vector)
                self.candidate_emails.append(candidate.user.email)
            
            # Save the updated index
            self.save_index(self.index_path)
        except Exception as e:
            raise Exception(f"Error adding candidate to index: {str(e)}")

    def _normalize_vector(self, vector: List[float]) -> List[float]:
        """Normalize a vector for cosine similarity."""
        vector = np.array(vector)
        norm = np.linalg.norm(vector)
        if norm == 0:
            return vector
        return vector / norm

    def search_similar_profiles(self, query_text: str, k: int = 10) -> List[Dict[str, Any]]:
        """Search for similar profiles based on a query using weighted multi-aspect search."""
        try:
            if not query_text:
                raise ValueError("Query text cannot be empty")

            if self.index.ntotal == 0:
                raise ValueError("No profiles in the search index. Please add some profiles first.")
            
            print(f"Starting search with query: {query_text}")
            
            # Parse the job description into different aspects
            try:
                parsed_jd = parse_job_description(query_text)
                print(f"Parsed job description sections: {list(parsed_jd.keys())}")
            except Exception as e:
                print(f"Error parsing job description: {str(e)}")
                raise Exception(f"Failed to parse job description: {str(e)}")
            
            # Generate query embeddings for different aspects
            query_embeddings = {}
            for aspect, text in parsed_jd.items():
                try:
                    embedding = get_embedding(text)
                    if not embedding or len(embedding) != self.dimension:
                        raise ValueError(f"Invalid embedding dimension for {aspect}")
                    query_embeddings[aspect] = embedding
                    print(f"Generated embedding for {aspect}")
                except Exception as e:
                    print(f"Error generating embedding for {aspect}: {str(e)}")
                    raise Exception(f"Failed to generate embedding for {aspect}: {str(e)}")
            
            # Normalize query embeddings
            try:
                normalized_queries = {
                    aspect: self._normalize_vector(embedding)
                    for aspect, embedding in query_embeddings.items()
                }
                print("Normalized all query embeddings")
            except Exception as e:
                print(f"Error normalizing embeddings: {str(e)}")
                raise Exception(f"Failed to normalize embeddings: {str(e)}")
            
            # Search for each aspect
            all_results = []
            for aspect, query_vector in normalized_queries.items():
                try:
                    query_array = np.array([query_vector], dtype=np.float32)
                    distances, indices = self.index.search(query_array, k)
                    print(f"Search completed for {aspect}")
                    
                    # Convert distances to similarity scores and apply weights
                    for i, idx in enumerate(indices[0]):
                        if idx < len(self.candidate_emails):
                            similarity = float(distances[0][i])  # Cosine similarity is already in [0,1]
                            weighted_score = similarity * self.weights[aspect]
                            all_results.append({
                                "email": self.candidate_emails[idx],
                                "aspect": aspect,
                                "similarity_score": weighted_score,
                                "aspect_query": parsed_jd[aspect]
                            })
                except Exception as e:
                    print(f"Error searching for aspect {aspect}: {str(e)}")
                    raise Exception(f"Failed to search for aspect {aspect}: {str(e)}")
            
            if not all_results:
                print("No results found in initial search")
                raise ValueError("No matching profiles found")
            
            # Combine results by email
            try:
                combined_results = {}
                for result in all_results:
                    email = result["email"]
                    if email not in combined_results:
                        combined_results[email] = {
                            "email": email,
                            "total_score": 0,
                            "aspect_scores": {},
                            "aspect_queries": {}
                        }
                    combined_results[email]["total_score"] += result["similarity_score"]
                    combined_results[email]["aspect_scores"][result["aspect"]] = result["similarity_score"]
                    combined_results[email]["aspect_queries"][result["aspect"]] = result["aspect_query"]
                print(f"Combined results for {len(combined_results)} candidates")
            except Exception as e:
                print(f"Error combining results: {str(e)}")
                raise Exception(f"Failed to combine results: {str(e)}")
            
            # Sort by total score and get top k results
            try:
                final_results = []
                for email, scores in sorted(
                    combined_results.items(),
                    key=lambda x: x[1]["total_score"],
                    reverse=True
                )[:k]:
                    try:
                        candidate = Candidate.objects.select_related('user').get(user__email=email)
                        final_results.append({
                            "email": email,
                            "name": candidate.name,
                            "total_similarity_score": scores["total_score"],
                            "aspect_scores": scores["aspect_scores"],
                            "aspect_queries": scores["aspect_queries"],
                            "current_role": candidate.current_job_title,
                            "company": candidate.current_company,
                            "user_token": candidate.user.auth_token.key if hasattr(candidate.user, 'auth_token') else None
                        })
                    except Candidate.DoesNotExist:
                        print(f"Warning: Candidate with email {email} not found in database")
                        continue
                    except Exception as e:
                        print(f"Warning: Error processing candidate {email}: {str(e)}")
                        continue
                
                if not final_results:
                    print("No final results after processing")
                    raise ValueError("No matching profiles found")
                
                print(f"Returning {len(final_results)} final results")
                return final_results
            except Exception as e:
                print(f"Error processing final results: {str(e)}")
                raise Exception(f"Failed to process final results: {str(e)}")
                
        except ValueError as ve:
            print(f"ValueError in search_similar_profiles: {str(ve)}")
            raise ValueError(str(ve))
        except Exception as e:
            print(f"Unexpected error in search_similar_profiles: {str(e)}")
            raise Exception(f"Error in search_similar_profiles: {str(e)}")

    def save_index(self, filepath: str) -> None:
        """Save the FAISS index and candidate emails to disk."""
        try:
            faiss.write_index(self.index, f"{filepath}.index")
            np.save(f"{filepath}_emails.npy", np.array(self.candidate_emails))
        except Exception as e:
            raise Exception(f"Error saving index: {str(e)}")

    def load_index(self, filepath: str) -> None:
        """Load the FAISS index and candidate emails from disk."""
        try:
            self.index = faiss.read_index(f"{filepath}.index")
            self.candidate_emails = np.load(f"{filepath}_emails.npy").tolist()
        except Exception as e:
            raise Exception(f"Error loading index: {str(e)}")

def initialize_index() -> None:
    """Initialize the FAISS index with all existing candidates."""
    try:
        # Get all candidates
        candidates = Candidate.objects.all()
        if not candidates.exists():
            print("No candidates found in the database")
            return

        print(f"Found {candidates.count()} candidates to index")
        
        # Clear existing index
        embedding_manager.index = faiss.IndexFlatIP(embedding_manager.dimension)
        embedding_manager.candidate_emails = []
        
        # Add each candidate to the index
        for candidate in candidates:
            try:
                embedding_manager.add_to_index(candidate)
                print(f"Added candidate {candidate.user.email} to index")
            except Exception as e:
                print(f"Error adding candidate {candidate.user.email} to index: {str(e)}")
                continue
        
        print("Index initialization completed")
    except Exception as e:
        print(f"Error initializing index: {str(e)}")
        raise Exception(f"Failed to initialize index: {str(e)}")

# Create a singleton instance
embedding_manager = ProfileEmbeddingManager()

def update_profile_embeddings(candidate_id: int) -> None:
    """Update embeddings for a specific candidate."""
    try:
        candidate = Candidate.objects.get(id=candidate_id)
        embedding_manager.add_to_index(candidate)
    except Exception as e:
        raise Exception(f"Error updating embeddings for candidate {candidate_id}: {str(e)}")

def search_candidates(query: str, k: int = 10) -> List[Dict[str, Any]]:
    """Search for candidates based on a query."""
    try:
        return embedding_manager.search_similar_profiles(query, k)
    except Exception as e:
        raise Exception(f"Error searching candidates: {str(e)}")