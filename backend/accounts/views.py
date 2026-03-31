from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_200_OK
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer
from .openai_service import OpenAIService
from .geonames_service import GeoNamesService


class RegisterView(APIView):
    """
    User Registration Endpoint
    POST /api/register/ - Create a new user account
    """
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token = Token.objects.create(user=user)
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data,
                'message': 'User registered successfully.'
            }, status=HTTP_201_CREATED)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    User Login Endpoint
    POST /api/login/ - Login with email and password
    """
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data,
                'message': 'Login successful.'
            }, status=HTTP_200_OK)
        print("LOGIN SERIALIZER ERRORS:", serializer.errors)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class ChatView(APIView):
    """
    Chat Reply Generator Endpoint
    POST /api/chat/ - Generate a natural reply to a conversation
    
    Uses OpenAI's GPT model to create unique, human-like responses.
    Tracks responses to ensure no repetition within a month period.
    """
    
    # Require authentication for this endpoint
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Generate an AI response to a pasted conversation
        
        Request body:
        {
            'conversation': 'Last 10 texts from a conversation as string'
        }
        
        Response:
        {
            'success': bool,
            'response': 'AI-generated reply',
            'is_unique': bool,
            'message': str
        }
        """
        
        try:
            # Get conversation text from request
            conversation = request.data.get('conversation', '')
            
            if not conversation or len(conversation.strip()) == 0:
                return Response({
                    'success': False,
                    'message': 'Please provide a conversation to reply to.'
                }, status=HTTP_400_BAD_REQUEST)
            
            # Generate response using OpenAI
            result = OpenAIService.generate_response(
                user_id=request.user.id,
                conversation_text=conversation
            )
            
            if not result['success']:
                return Response({
                    'success': False,
                    'message': f'Error generating response: {result.get("error", "Unknown error")}'
                }, status=HTTP_400_BAD_REQUEST)
            
            # Return successful response
            return Response({
                'success': True,
                'response': result['response'],
                'is_unique': result['is_unique'],
                'message': 'Response generated successfully!'
            }, status=HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Server error: {str(e)}'
            }, status=HTTP_400_BAD_REQUEST)


class LocationSearchView(APIView):
    """
    Location Search Endpoint
    GET /api/locations/?state=StateName - Find cities 45 mins away from a state
    
    Uses GeoNames API to find cities within a specific radius from state center.
    45 minutes driving time is approximated as 75 km radius.
    """
    
    # Require authentication for this endpoint
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Search for cities within 45 minutes of a city+state or state center.
        Query parameters:
        - city: Name of the city (optional)
        - state: Name of the state (required)
        """
        try:
            city = request.query_params.get('city', '').strip()
            state = request.query_params.get('state', '').strip()
            if not state:
                return Response({
                    'success': False,
                    'message': 'Please provide a state name. Example: ?state=Virginia'
                }, status=HTTP_400_BAD_REQUEST)
            result = GeoNamesService.get_cities_45_mins_away(city=city, state=state)
            if not result['success']:
                return Response({
                    'success': False,
                    'message': result.get('error', 'Could not search for locations')
                }, status=HTTP_400_BAD_REQUEST)
            return Response({
                'success': True,
                'cities': result['cities'],
                'count': result['count'],
                'center': result['center'],
                'search_radius_km': result['search_radius_km'],
                'message': f'Found {result["count"]} cities within 45 minutes of {city+", " if city else ""}{state}'
            }, status=HTTP_200_OK)
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Server error: {str(e)}'
            }, status=HTTP_400_BAD_REQUEST)
