from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .profile_embeddings import update_profile_embeddings, search_candidates
from .models import Candidate

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_embeddings(request):
    """
    Update embeddings for a candidate profile.
    This endpoint should be called whenever a profile is updated.
    """
    try:
        candidate = Candidate.objects.get(user=request.user)
        update_profile_embeddings(candidate.id)
        return Response({
            'message': 'Profile embeddings updated successfully'
        })
    except Candidate.DoesNotExist:
        return Response({
            'error': 'Candidate profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Error updating embeddings: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_similar_profiles(request):
    """
    Search for similar profiles based on a query.
    Query parameter 'q' should contain the search text or full job description.
    Optional parameter 'k' specifies the number of results (default: 10).
    Returns results with weighted scores for different aspects of the profile.
    """
    query = request.query_params.get('q')
    try:
        k = int(request.query_params.get('k', 10))
    except ValueError:
        return Response({
            'error': 'Invalid value for parameter "k". Must be a number.'
        }, status=status.HTTP_400_BAD_REQUEST)

    if not query:
        return Response({
            'error': 'Query parameter "q" is required'
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
                    'location': result['aspect_scores'].get('location', 0)
                },
                'aspect_queries': {
                    'profile': result['aspect_queries'].get('profile', ''),
                    'skills': result['aspect_queries'].get('skills', ''),
                    'experience': result['aspect_queries'].get('experience', ''),
                    'projects': result['aspect_queries'].get('projects', ''),
                    'location': result['aspect_queries'].get('location', '')
                },
                'user_token': result.get('user_token')
            }
            formatted_results.append(formatted_result)
            
        return Response({
            'results': formatted_results,
            'query': query,
            'count': len(formatted_results),
            'weights': {
                'profile': 0.3,
                'skills': 0.3,
                'experience': 0.2,
                'projects': 0.1,
                'location': 0.1
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