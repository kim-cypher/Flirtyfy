import logging
import hashlib
logger = logging.getLogger(__name__)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_200_OK
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer
from .services.button_generator import generate_button_response
from .services.intent_detector import detect_intent, generate_context_aware_response
from .novelty_models import AIReply, ConversationUpload


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
            logger.info(f"User registered: {user.username} ({user.id})")
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data,
                'message': 'User registered successfully.'
            }, status=HTTP_201_CREATED)
        logger.warning(f"Registration failed: {serializer.errors}")
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
            logger.info(f"User login: {user.username} ({user.id})")
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data,
                'message': 'Login successful.'
            }, status=HTTP_200_OK)
        logger.warning(f"Login failed: {serializer.errors}")
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


class GenerateSpecificResponseView(APIView):
    """
    Context-Aware Response Generator (LEFT SIDE)
    POST /api/chat/generate-specific/ - Generate response from pasted conversation
    
    Uses GPT-4-mini to analyze pasted conversation and generate context-aware reply.
    Detects conversation stage, tone, topic, and energy level.
    """
    
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Generate context-aware response from pasted conversation
        
        Request body:
        {
            'conversation': 'Pasted conversation text (min 20 chars, max 10000)'
        }
        
        Response:
        {
            'success': bool,
            'response': 'Generated reply',
            'intent': {topic, tone, stage, energy},
            'message': str
        }
        """
        try:
            conversation = request.data.get('conversation', '').strip()
            
            # Validate input
            if not conversation:
                return Response({
                    'success': False,
                    'message': 'Please provide a conversation to analyze.'
                }, status=HTTP_400_BAD_REQUEST)
            
            if len(conversation) < 20:
                return Response({
                    'success': False,
                    'message': 'Conversation must be at least 20 characters.'
                }, status=HTTP_400_BAD_REQUEST)
            
            if len(conversation) > 10000:
                return Response({
                    'success': False,
                    'message': 'Conversation cannot exceed 10000 characters.'
                }, status=HTTP_400_BAD_REQUEST)
            
            # Detect intent from conversation
            intent_data = detect_intent(conversation)
            if not intent_data:
                return Response({
                    'success': False,
                    'message': 'Could not analyze conversation intent.'
                }, status=HTTP_400_BAD_REQUEST)
            
            # Generate context-aware response
            response_result = generate_context_aware_response(conversation, intent_data)
            if not response_result or 'error' in response_result:
                return Response({
                    'success': False,
                    'message': response_result.get('error', 'Could not generate response')
                }, status=HTTP_400_BAD_REQUEST)
            
            # Save to database
            try:
                # Try to get or create a dummy upload if none exists
                upload = ConversationUpload.objects.create(
                    user=request.user,
                    original_text=conversation
                )
                
                AIReply.objects.create(
                    user=request.user,
                    upload=upload,
                    original_text=conversation,
                    normalized_text=conversation,
                    embedding=None,  # Could add embeddings later
                    fingerprint=hashlib.md5(conversation.encode()).hexdigest(),
                    summary=response_result.get('summary', ''),
                    intent=intent_data.get('topic', 'unknown'),
                    status='completed',
                    conversation_context=conversation,
                    intent_type='specific',
                    button_intent=None
                )
            except Exception as db_error:
                logger.error(f"Database error saving response: {str(db_error)}")
                # Don't fail the request if DB save fails
            
            return Response({
                'success': True,
                'response': response_result.get('response', ''),
                'intent': intent_data,
                'message': 'Response generated successfully!'
            }, status=HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error in generate_specific_response: {str(e)}")
            return Response({
                'success': False,
                'message': f'Server error: {str(e)}'
            }, status=HTTP_400_BAD_REQUEST)


class GenerateButtonResponseView(APIView):
    """
    Button-Based Response Generator (RIGHT SIDE)
    POST /api/chat/generate-button/ - Generate response from button click
    
    Uses GPT-3.5-turbo to generate random scenario responses based on intent button.
    Prevents theme repetition within 24-hour session window.
    """
    
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Generate button response
        
        Request body:
        {
            'button_intent': 'Button name (e.g., morning_flirt, sensual, etc.)'
        }
        
        Response:
        {
            'success': bool,
            'response': 'Generated reply',
            'theme': 'Detected theme',
            'message': str
        }
        """
        try:
            button_intent = request.data.get('button_intent', '').strip()
            
            # Validate button intent
            if not button_intent:
                return Response({
                    'success': False,
                    'message': 'Please provide a button_intent.'
                }, status=HTTP_400_BAD_REQUEST)
            
            # Generate button response
            response_result = generate_button_response(request.user.id, button_intent)
            if 'error' in response_result:
                return Response({
                    'success': False,
                    'message': response_result.get('error', 'Could not generate response')
                }, status=HTTP_400_BAD_REQUEST)
            
            # Save to database
            try:
                # Try to get or create a dummy upload if none exists
                upload = ConversationUpload.objects.create(
                    user=request.user,
                    original_text=f'Button: {button_intent}'
                )
                
                AIReply.objects.create(
                    user=request.user,
                    upload=upload,
                    original_text=f'Button: {button_intent}',
                    normalized_text=f'Button: {button_intent}',
                    embedding=None,
                    fingerprint=hashlib.md5(button_intent.encode()).hexdigest(),
                    summary=f'Generated from button: {button_intent}',
                    intent=button_intent,
                    status='completed',
                    conversation_context=None,
                    intent_type='button',
                    button_intent=button_intent
                )
            except Exception as db_error:
                logger.error(f"Database error saving button response: {str(db_error)}")
                # Don't fail the request if DB save fails
            
            return Response({
                'success': True,
                'response': response_result.get('response', ''),
                'theme': response_result.get('theme', ''),
                'message': 'Response generated successfully!'
            }, status=HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error in generate_button_response: {str(e)}")
            return Response({
                'success': False,
                'message': f'Server error: {str(e)}'
            }, status=HTTP_400_BAD_REQUEST)
