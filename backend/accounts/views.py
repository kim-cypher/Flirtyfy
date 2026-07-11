import re
import logging
import hashlib
from datetime import timedelta
from django.utils import timezone
logger = logging.getLogger(__name__)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.status import (
    HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_200_OK,
    HTTP_402_PAYMENT_REQUIRED, HTTP_404_NOT_FOUND, HTTP_503_SERVICE_UNAVAILABLE,
)
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import TokenAuthentication
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, PasswordResetSerializer
from .services.button_generator import generate_button_response
from .services.intent_detector import detect_intent, generate_context_aware_response
from .services.safety_filter import SafetyFilter
from .services.intent_template_classifier import get_content_fingerprint, get_template_key
from .services.credits import get_available_clicks, try_consume_click, get_or_create_credits, gate_check
from .services import mpesa_service
from .throttles import (
    GenerationBurstThrottle, GenerationDailyThrottle, PaymentInitiateThrottle,
    LoginThrottle, RegisterThrottle, PasswordResetThrottle,
)
from django.core.cache import cache
from django.conf import settings
from .novelty_models import AIReply, AIReplyFeedback, ConversationUpload
from .models import Notification, Payment

_safety = SafetyFilter()


def _normalize_text(text: str) -> str:
    import unicodedata
    text = unicodedata.normalize('NFKC', text).lower()
    text = re.sub(r'[^\w\s]', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def _response_fingerprint(text: str) -> str:
    return hashlib.sha256(_normalize_text(text).encode()).hexdigest()


def _is_exact_duplicate(user, text: str) -> bool:
    """Layer 1: exact/near-exact text match."""
    fp = _response_fingerprint(text)
    return AIReply.objects.filter(user=user, fingerprint=fp).exists()


def _is_intent_duplicate(user, text: str) -> bool:
    """Layer 2: same question intent, different words. Pure Python + indexed DB lookup.
    Skips generic_question fallback — unclassified messages don't block each other."""
    template = get_template_key(text)
    if template == 'generic_question':
        return False
    cfp = get_content_fingerprint(text)
    return AIReply.objects.filter(user=user, content_fingerprint=cfp).exists()


def _is_duplicate(user, text: str) -> tuple:
    """
    Run Layer 1 + Layer 2 dedup checks.
    Returns (is_duplicate: bool, reason: str)
    """
    if _is_exact_duplicate(user, text):
        return True, 'exact'
    if _is_intent_duplicate(user, text):
        return True, 'intent'
    return False, ''


# Max new accounts per IP per rolling day. With WELCOME_CLICKS=5, farming
# free clicks now requires a new network per 3 accounts — more effort than
# the ~15 free clicks are worth.
_SIGNUPS_PER_IP_PER_DAY = 3


def _client_ip(request) -> str:
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


class RegisterView(APIView):
    """
    User Registration Endpoint
    POST /api/register/ - Create a new user account
    """
    throttle_classes = [RegisterThrottle]

    def post(self, request):
        ip = _client_ip(request)
        ip_key = f'signup_ip_{ip}'
        try:
            signup_count = int(cache.get(ip_key) or 0)
        except Exception:
            signup_count = 0
        if signup_count >= _SIGNUPS_PER_IP_PER_DAY:
            logger.warning(f"Signup cap hit for IP {ip}")
            return Response(
                {'message': 'Too many new accounts from this network today. Please try again tomorrow.'},
                status=HTTP_400_BAD_REQUEST,
            )

        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token = Token.objects.create(user=user)
            try:
                cache.set(ip_key, signup_count + 1, 86400)
            except Exception:
                pass
            logger.info(f"User registered: {user.username} ({user.id}) from {ip}")
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
    throttle_classes = [LoginThrottle]

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



class PasswordResetView(APIView):
    """
    POST /api/password-reset/ - Reset a forgotten password using
    (email, first_name) as the identity check instead of an email link.
    Body: {email, first_name, new_password, confirm_new_password}
    """
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            user.set_password(serializer.validated_data['new_password'])
            user.save(update_fields=['password'])
            # Invalidate any existing session token — old token shouldn't
            # keep working once the password it was issued under is gone.
            Token.objects.filter(user=user).delete()
            logger.info(f"Password reset for user: {user.username} ({user.id})")
            return Response({'message': 'Your password has been reset. Please log in.'}, status=HTTP_200_OK)
        logger.warning(f"Password reset failed: {serializer.errors}")
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class GenerateSpecificResponseView(APIView):
    """
    Context-Aware Response Generator (LEFT SIDE)
    POST /api/chat/generate-specific/ - Generate response from pasted conversation
    
    Uses GPT-4-mini to analyze pasted conversation and generate context-aware reply.
    Detects conversation stage, tone, topic, and energy level.
    """
    
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [GenerationBurstThrottle, GenerationDailyThrottle]

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
            time_slot = request.data.get('time_slot', None) or None
            try:
                his_last_n = max(1, min(5, int(request.data.get('his_last_n', 1))))
            except (TypeError, ValueError):
                his_last_n = 1

            if not conversation:
                return Response({'success': False, 'message': 'Please provide a conversation.'}, status=HTTP_400_BAD_REQUEST)
            if len(conversation) < 20:
                return Response({'success': False, 'message': 'Conversation must be at least 20 characters.'}, status=HTTP_400_BAD_REQUEST)
            if len(conversation) > 10000:
                return Response({'success': False, 'message': 'Conversation cannot exceed 10000 characters.'}, status=HTTP_400_BAD_REQUEST)

            # Click gate — advisory check before spending any LLM cost. The actual
            # deduction (after success, below) is what's atomic/authoritative.
            if not gate_check(request.user):
                return Response(
                    {'success': False, 'message': "You're out of clicks.", 'out_of_clicks': True},
                    status=HTTP_402_PAYMENT_REQUIRED,
                )

            # Safety check — blocks CSAM/violence/trafficking only; sexual content is allowed
            is_safe, violation_type, safe_response = _safety.check_safety(conversation)
            if not is_safe:
                return Response({'success': False, 'message': safe_response}, status=HTTP_400_BAD_REQUEST)

            # Pure-Python intent detection (zero API cost)
            intent_data = detect_intent(conversation)

            # Read recent replies from Redis for variety injection (same pattern as button panel)
            _recent_replies = []
            try:
                _spec_session = cache.get(f"user_specific_{request.user.id}") or {}
                _recent_replies = _spec_session.get('recent_replies', [])
            except Exception:
                pass

            # Same-conversation guarantee: if this exact conversation was
            # uploaded before (user clicked generate again), every reply we
            # already gave for it goes to the FRONT of the avoid list, so the
            # model is steered away proactively (the dedup layers remain the
            # enforcement backstop). Pure DB lookup — zero LLM cost.
            conv_fp = _response_fingerprint(conversation)
            try:
                _same_convo = list(
                    AIReply.objects
                    .filter(user=request.user, conversation_fingerprint=conv_fp)
                    .exclude(delivered_text='')
                    .order_by('-created_at')
                    .values_list('delivered_text', flat=True)[:4]
                )
                _recent_replies = (_same_convo + [r for r in _recent_replies if r not in _same_convo])[:5]
            except Exception:
                pass

            # Generate response (one LLM call)
            response_result = generate_context_aware_response(
                conversation, intent_data, _recent_replies, time_slot=time_slot,
                user_id=request.user.id, his_last_n=his_last_n,
            )
            if 'error' in response_result:
                return Response({'success': False, 'message': response_result['error']}, status=HTTP_400_BAD_REQUEST)

            response_text = response_result.get('response', '')

            # Push new reply to Redis session — keeps last 3 for next generation's variety injection
            try:
                _spec_key = f"user_specific_{request.user.id}"
                _spec_session = cache.get(_spec_key) or {}
                _prev = _spec_session.get('recent_replies', [])
                _spec_session['recent_replies'] = ([response_text] + _prev)[:3]
                cache.set(_spec_key, _spec_session, 86400)
            except Exception:
                pass

            # Save to DB for dedup tracking
            saved_reply_id = None
            try:
                upload = ConversationUpload.objects.create(
                    user=request.user,
                    original_text=conversation,
                )
                reply = AIReply.objects.create(
                    user=request.user,
                    upload=upload,
                    original_text=conversation,
                    normalized_text=_normalize_text(response_text),
                    embedding=None,
                    fingerprint=_response_fingerprint(response_text),
                    content_fingerprint=get_content_fingerprint(response_text),
                    summary='',
                    intent=intent_data.get('topic', 'general'),
                    status='complete',
                    expires_at=timezone.now() + timedelta(days=30),
                    conversation_context=conversation,
                    intent_type='specific',
                    button_intent=None,
                    delivered_text=response_text,
                    conversation_fingerprint=conv_fp,
                )
                saved_reply_id = reply.id
                # Near-duplicate detection is synchronous now (pg_trgm in
                # dedup.dedupe_similar) — no background embedding task needed.
            except Exception as db_error:
                logger.error(f"DB save error (specific): {db_error}")

            try_consume_click(request.user)

            return Response({
                'success': True,
                'response': response_text,
                'reply_id': saved_reply_id,
                'intent': intent_data,
                'message': 'Response generated successfully!',
            }, status=HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in GenerateSpecificResponseView: {e}")
            return Response({'success': False, 'message': f'Server error: {e}'}, status=HTTP_400_BAD_REQUEST)


class GenerateButtonResponseView(APIView):
    """
    Button-Based Response Generator (RIGHT SIDE)
    POST /api/chat/generate-button/ - Generate response from button click
    
    Uses GPT-3.5-turbo to generate random scenario responses based on intent button.
    Prevents theme repetition within 24-hour session window.
    """
    
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [GenerationBurstThrottle, GenerationDailyThrottle]

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
            time_slot = request.data.get('time_slot', None) or None

            if not button_intent:
                return Response({'success': False, 'message': 'Please provide a button_intent.'}, status=HTTP_400_BAD_REQUEST)

            # Click gate — advisory check before spending any LLM cost. The actual
            # deduction (after success, below) is what's atomic/authoritative.
            if not gate_check(request.user):
                return Response(
                    {'success': False, 'message': "You're out of clicks.", 'out_of_clicks': True},
                    status=HTTP_402_PAYMENT_REQUIRED,
                )

            # Try up to 3 times to get a response that hasn't been sent before
            response_text = None
            theme = ''
            status_val = 'complete'
            last_result = None

            # A couple of server-side attempts is plenty — the avoid-list makes
            # collisions rare, and each attempt is a full generation, so 6 was
            # pure waste. The frontend still auto-retries silently on top of this.
            for attempt in range(2):
                result = generate_button_response(request.user.id, button_intent, time_slot=time_slot)
                if 'error' in result:
                    return Response({'success': False, 'message': result['error']}, status=HTTP_400_BAD_REQUEST)
                last_result = result
                candidate = result.get('response', '')
                is_dup, dup_reason = _is_duplicate(request.user, candidate)
                if not is_dup:
                    response_text = candidate
                    theme = result.get('theme', '')
                    break
                logger.info(f"Duplicate ({dup_reason}) on attempt {attempt + 1} for user {request.user.id}, retrying...")

            if response_text is None:
                # All attempts were near-duplicates. On the target dating platform
                # a repeated message can get the user's account BANNED, so we must
                # NOT ship a known duplicate. Refuse cleanly, do NOT charge the
                # click, and ask them to tap again (rotation will land elsewhere).
                logger.warning(
                    f"Button all-duplicate for user {request.user.id} intent {button_intent} — refusing to ship"
                )
                return Response(
                    {'success': False,
                     'message': 'Give it another tap — crafting something fresh for you.',
                     'retry': True},
                    status=HTTP_200_OK,
                )

            # Save to DB — fingerprint the actual response text for future dedup
            saved_reply_id = None
            try:
                upload = ConversationUpload.objects.create(
                    user=request.user,
                    original_text=f'Button: {button_intent}',
                )
                reply = AIReply.objects.create(
                    user=request.user,
                    upload=upload,
                    original_text=f'Button: {button_intent}',
                    normalized_text=_normalize_text(response_text),
                    embedding=None,
                    fingerprint=_response_fingerprint(response_text),
                    content_fingerprint=get_content_fingerprint(response_text),
                    summary='',
                    intent=button_intent,
                    status=status_val,
                    expires_at=timezone.now() + timedelta(days=30),
                    conversation_context=None,
                    intent_type='button',
                    button_intent=button_intent,
                    delivered_text=response_text,
                )
                saved_reply_id = reply.id
                # Near-duplicate detection is synchronous now (pg_trgm in
                # dedup.dedupe_similar) — no background embedding task needed.
            except Exception as db_error:
                logger.error(f"DB save error (button): {db_error}")

            try_consume_click(request.user)

            return Response({
                'success': True,
                'response': response_text,
                'reply_id': saved_reply_id,
                'theme': theme,
                'message': 'Response generated successfully!',
            }, status=HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in GenerateButtonResponseView: {e}")
            return Response({'success': False, 'message': f'Server error: {e}'}, status=HTTP_400_BAD_REQUEST)


class ReplyFeedbackView(APIView):
    """
    User rating for a delivered reply — the human side of the quality loop.
    POST /api/chat/feedback/  {reply_id, rating: excellent|good|bad}

    One rating per user per reply (re-rating overwrites). Stored on
    AIReplyFeedback.reason so weekly reviews can join user ratings against
    judge scores and delivered text.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    RATINGS = ('excellent', 'good', 'bad')

    def post(self, request):
        rating = str(request.data.get('rating', '')).strip().lower()
        if rating not in self.RATINGS:
            return Response(
                {'success': False, 'message': 'Rating must be excellent, good, or bad.'},
                status=HTTP_400_BAD_REQUEST,
            )
        try:
            reply = AIReply.objects.get(id=int(request.data.get('reply_id')), user=request.user)
        except (AIReply.DoesNotExist, TypeError, ValueError):
            return Response(
                {'success': False, 'message': 'Reply not found.'},
                status=HTTP_400_BAD_REQUEST,
            )

        AIReplyFeedback.objects.update_or_create(
            user=request.user, reply=reply, defaults={'reason': rating},
        )
        return Response({'success': True, 'message': 'Thanks for the feedback!'}, status=HTTP_200_OK)


class CreditsView(APIView):
    """
    GET /api/credits/ - Current click balance + referral info for the logged-in
    user. Tied to the account server-side, so it's identical no matter which
    device/browser this user is logged in from.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        credits = get_or_create_credits(request.user)
        origin = request.build_absolute_uri('/').rstrip('/')
        return Response({
            'success': True,
            'is_premium': credits.is_premium,
            'available_clicks': credits.available_clicks(),
            'referral_code': credits.referral_code,
            'referral_link': f"{origin}/register?ref={credits.referral_code}",
            'plans': {
                'topup':  {'price_kes': settings.TOPUP_PRICE_KES,  'clicks': settings.TOPUP_CLICKS},
                'weekly': {'price_kes': settings.WEEKLY_PRICE_KES, 'clicks': settings.WEEKLY_CLICKS,
                           'days': settings.WEEKLY_EXPIRY_DAYS},
            },
            # Back-compat for any UI still reading the old keys.
            'subscription_price_kes': settings.TOPUP_PRICE_KES,
            'subscription_clicks': settings.TOPUP_CLICKS,
        })


class NotificationListView(APIView):
    """
    GET /api/notifications/ - Last 30 notifications + unread count.
    Frontend polls this (no websockets) to drive the notification bell.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user)[:30]
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({
            'success': True,
            'unread_count': unread_count,
            'notifications': [
                {
                    'id': n.id,
                    'type': n.type,
                    'title': n.title,
                    'body': n.body,
                    'is_read': n.is_read,
                    'created_at': n.created_at.isoformat(),
                }
                for n in notifications
            ],
        })


class NotificationMarkReadView(APIView):
    """
    POST /api/notifications/mark-read/
    Body: {"id": <int>} marks one notification read, or {"all": true} marks all.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.data.get('all'):
            Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
            return Response({'success': True})

        notif_id = request.data.get('id')
        if not notif_id:
            return Response({'success': False, 'message': 'Provide an id or all=true.'}, status=HTTP_400_BAD_REQUEST)
        updated = Notification.objects.filter(user=request.user, id=notif_id).update(is_read=True)
        if not updated:
            return Response({'success': False, 'message': 'Notification not found.'}, status=HTTP_404_NOT_FOUND)
        return Response({'success': True})


class InitiatePaymentView(APIView):
    """
    POST /api/payments/initiate/
    Body: {"phone_number": "07XXXXXXXX"}
    Triggers an M-Pesa STK push to the given phone for SUBSCRIPTION_PRICE_KES.
    Frontend should poll PaymentStatusView with the returned checkout_request_id.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [PaymentInitiateThrottle]

    def post(self, request):
        phone_number = request.data.get('phone_number', '').strip()
        if not phone_number:
            return Response({'success': False, 'message': 'Please provide a phone number.'}, status=HTTP_400_BAD_REQUEST)

        # Which plan: weekly bundle or one-off top-up (default).
        plan = str(request.data.get('plan', 'topup')).strip().lower()
        if plan == 'weekly':
            amount_kes = settings.WEEKLY_PRICE_KES
            clicks_granted = settings.WEEKLY_CLICKS
        else:
            plan = 'topup'
            amount_kes = settings.TOPUP_PRICE_KES
            clicks_granted = settings.TOPUP_CLICKS

        if not (settings.MPESA_CONSUMER_KEY and settings.MPESA_PASSKEY and settings.MPESA_CALLBACK_URL):
            logger.error("Payment attempted but M-Pesa credentials are not configured")
            return Response(
                {'success': False, 'message': 'Payments are not set up yet. Please try again later.'},
                status=HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            result = mpesa_service.initiate_stk_push(phone_number, amount_kes)
        except Exception as e:
            logger.error(f"M-Pesa STK push failed for user {request.user.id}: {e}")
            return Response(
                {'success': False, 'message': 'Could not start the payment. Please try again.'},
                status=HTTP_400_BAD_REQUEST,
            )

        checkout_request_id = result.get('CheckoutRequestID')
        if not checkout_request_id:
            logger.error(f"M-Pesa STK push returned no CheckoutRequestID: {result}")
            return Response(
                {'success': False, 'message': 'Could not start the payment. Please try again.'},
                status=HTTP_400_BAD_REQUEST,
            )

        Payment.objects.create(
            user=request.user,
            phone_number=mpesa_service.normalize_phone(phone_number),
            plan=plan,
            amount_kes=amount_kes,
            clicks_granted=clicks_granted,
            checkout_request_id=checkout_request_id,
            merchant_request_id=result.get('MerchantRequestID', ''),
            status='pending',
        )

        return Response({
            'success': True,
            'checkout_request_id': checkout_request_id,
            'message': 'Check your phone to complete the payment.',
        })


class PaymentStatusView(APIView):
    """
    GET /api/payments/status/<checkout_request_id>/
    Frontend polls this after InitiatePaymentView while the user completes
    the prompt on their phone.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, checkout_request_id):
        try:
            payment = Payment.objects.get(checkout_request_id=checkout_request_id, user=request.user)
        except Payment.DoesNotExist:
            return Response({'success': False, 'message': 'Payment not found.'}, status=HTTP_404_NOT_FOUND)

        return Response({
            'success': True,
            'status': payment.status,
            'clicks_granted': payment.clicks_granted if payment.status == 'success' else None,
        })


class MpesaCallbackView(APIView):
    """
    POST /api/payments/mpesa-callback/
    Safaricom calls this directly — there is no user context on their side,
    so this view takes no auth. That also means it has NO authentication of
    its OWN: CheckoutRequestID is returned to the paying user's browser by
    InitiatePaymentView, so anyone could POST a forged "success" body here
    for their own pending payment. The callback is therefore treated only
    as a trigger to go check — never as proof. The actual crediting decision
    is made by independently querying Safaricom's STK status endpoint with
    our own credentials (mpesa_service.query_stk_status), which only
    Safaricom can answer correctly.

    Identifies the Payment by CheckoutRequestID and is idempotent: a
    Payment already marked success/failed/cancelled is left alone even if
    Safaricom retries the callback (which it does on anything other than a
    200 response).
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        logger.info(f"M-Pesa callback received: {data}")
        try:
            parsed = mpesa_service.parse_callback(data)
        except Exception as e:
            logger.error(f"Failed to parse M-Pesa callback: {e}")
            return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})

        checkout_request_id = parsed.get('checkout_request_id')
        if not checkout_request_id:
            return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})

        try:
            payment = Payment.objects.get(checkout_request_id=checkout_request_id)
        except Payment.DoesNotExist:
            logger.warning(f"M-Pesa callback for unknown checkout_request_id: {checkout_request_id}")
            return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})

        if payment.status != 'pending':
            # Already processed — this is Safaricom retrying. Idempotent no-op.
            return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})

        # Authoritative check — ignores parsed['success'] entirely. The
        # callback body only tells us WHICH payment to go verify.
        try:
            verified = mpesa_service.query_stk_status(checkout_request_id)
        except Exception as e:
            # Cannot confirm either way — leave status as 'pending' rather than
            # guessing. Logged loudly so this can be investigated/resolved
            # manually (e.g. via admin) rather than silently crediting or
            # silently failing a real payment on a transient network error.
            logger.error(f"M-Pesa status query failed for {checkout_request_id}: {e}")
            payment.raw_callback = data
            payment.save(update_fields=['raw_callback', 'updated_at'])
            return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})

        payment.raw_callback = {'callback': data, 'verified_query': verified}
        if verified['success']:
            payment.status = 'success'
            payment.mpesa_receipt_number = parsed.get('receipt_number', '')
            payment.save(update_fields=['status', 'mpesa_receipt_number', 'raw_callback', 'updated_at'])

            from .services.credits import grant_credits
            from .services.notifications import create_notification
            # Weekly bundle lapses after 7 days; top-up does not expire.
            expiry = settings.WEEKLY_EXPIRY_DAYS if payment.plan == 'weekly' else None
            grant_credits(payment.user, payment.clicks_granted, 'purchase', expires_in_days=expiry)
            create_notification(
                payment.user, 'payment_success', "Payment received!",
                f"Your payment of {payment.amount_kes} KES went through. "
                f"{payment.clicks_granted} clicks have been added to your account."
            )
        else:
            payment.status = 'cancelled' if 'cancel' in verified['result_desc'].lower() else 'failed'
            payment.save(update_fields=['status', 'raw_callback', 'updated_at'])
            from .services.notifications import create_notification
            create_notification(
                payment.user, 'payment_failed', "Payment did not go through",
                "Your M-Pesa payment was not completed. Feel free to try again."
            )

        return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})
