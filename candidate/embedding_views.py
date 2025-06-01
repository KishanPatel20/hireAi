from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from .profile_embeddings import ProfileEmbeddingManager, search_candidates
from .models import Candidate

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_embeddings(request):
    """
    Update embeddings for a candidate profile.
    This endpoint should be called whenever a profile is updated.
    
    Request Body:
    {
        "token": "user_auth_token"  # Optional, if not provided will use request.user
    }
    
    Response:
    {
        "message": "Profile embeddings updated successfully",
        "embeddings": {
            "profile": [...],
            "skills": [...],
            "experience": [...],
            "projects": [...],
            "education": [...],
            "location": [...],
            "additional": [...]
        }
    }
    """
    try:
        # Get token from request body or use authenticated user
        token = request.data.get('token')
        if token:
            user = Token.objects.get(key=token).user
        else:
            user = request.user

        # Get candidate profile
        candidate = Candidate.objects.select_related('user').get(user=user)
        
        # Generate new embeddings
        embedding_manager = ProfileEmbeddingManager()
        embeddings = embedding_manager.generate_embeddings(candidate)
        
        # Add to index
        embedding_manager.add_to_index(candidate)
        
        return Response({
            'message': 'Profile embeddings updated successfully',
            'embeddings': {
                'profile': embeddings['profile_embedding'],
                'skills': embeddings['skills_embedding'],
                'experience': embeddings['experience_embedding'],
                'projects': embeddings['projects_embedding'],
                'education': embeddings['education_embedding'],
                'location': embeddings['location_embedding'],
                'additional': embeddings['additional_embedding']
            }
        })
    except Token.DoesNotExist:
        return Response({
            'error': 'Invalid token'
        }, status=status.HTTP_401_UNAUTHORIZED)
    except Candidate.DoesNotExist:
        return Response({
            'error': 'Candidate profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Error updating embeddings: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def search_similar_profiles(request):
    """
    Search for similar profiles based on a query.
    Request Body:
    {
        "q": "search text or job description",
        "k": 10  # optional, default 10
    }
    Returns results with weighted scores for different aspects of the profile.
    """
    query = request.data.get('q')
    try:
        k = int(request.data.get('k', 10))
    except ValueError:
        return Response({
            'error': 'Invalid value for parameter "k". Must be a number.'
        }, status=status.HTTP_400_BAD_REQUEST)

    if not query:
        return Response({
            'error': 'Field "q" is required in the request body.'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        results = search_candidates(query, k)
        if not results:
            return Response({
                'message': 'No similar profiles found',
                'query': query,
                'count': 0,
                'results': []
            })
        
        # Format the response to include aspect scores and queries
        formatted_results = []
        for result in results:
            formatted_result = {
                'email': result['email'],
                'name': result['name'],
                'current_role': result['current_role'],
                'company': result['company'],
                'total_similarity_score': result['total_similarity_score'],
                'aspect_scores': {
                    'profile': result['aspect_scores'].get('profile', 0),
                    'skills': result['aspect_scores'].get('skills', 0),
                    'experience': result['aspect_scores'].get('experience', 0),
                    'projects': result['aspect_scores'].get('projects', 0),
                    'education': result['aspect_scores'].get('education', 0),
                    'location': result['aspect_scores'].get('location', 0),
                    'additional': result['aspect_scores'].get('additional', 0)
                },
                'aspect_queries': {
                    'profile': result['aspect_queries'].get('profile', ''),
                    'skills': result['aspect_queries'].get('skills', ''),
                    'experience': result['aspect_queries'].get('experience', ''),
                    'projects': result['aspect_queries'].get('projects', ''),
                    'education': result['aspect_queries'].get('education', ''),
                    'location': result['aspect_queries'].get('location', ''),
                    'additional': result['aspect_queries'].get('additional', '')
                },
                'user_token': result.get('user_token')
            }
            formatted_results.append(formatted_result)
            
        return Response({
            'results': formatted_results,
            'query': query,
            'count': len(formatted_results),
            'weights': {
                'profile': 0.2,
                'skills': 0.25,
                'experience': 0.2,
                'projects': 0.15,
                'education': 0.1,
                'location': 0.05,
                'additional': 0.05
            }
        })
    except ValueError as ve:
        error_message = str(ve)
        if "No profiles in the search index" in error_message:
            return Response({
                'error': 'No profiles available for search. Please add some profiles first.',
                'query': query
            }, status=status.HTTP_404_NOT_FOUND)
        elif "No matching profiles found" in error_message:
            return Response({
                'message': 'No similar profiles found',
                'query': query,
                'count': 0,
                'results': []
            })
        return Response({
            'error': f'Invalid search request: {error_message}'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        error_message = str(e)
        return Response({
            'error': f'Error searching profiles: {error_message}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 