from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from accounts.novelty_models import AIReply


class Command(BaseCommand):
    help = (
        'Inspect what the system delivered to users — quality monitoring at zero LLM cost. '
        'Examples:\n'
        '  python manage.py recent_replies --days 7 --user 3\n'
        '  python manage.py recent_replies --type button --button new_match --limit 30\n'
        '  python manage.py recent_replies --repeats   (conversations generated 2+ times, with every reply)'
    )

    def add_arguments(self, parser):
        parser.add_argument('--user', type=int, default=None, help='Filter by user id')
        parser.add_argument('--limit', type=int, default=10, help='Number of replies to show (default 10)')
        parser.add_argument('--days', type=int, default=None, help='Only replies from the last N days')
        parser.add_argument('--type', type=str, default=None, choices=['specific', 'button'],
                            help='specific = left panel, button = right panel')
        parser.add_argument('--button', type=str, default=None, help='Filter by button_intent (e.g. vulnerability)')
        parser.add_argument('--full', action='store_true', help='Show full text instead of truncating to 200 chars')
        parser.add_argument('--repeats', action='store_true',
                            help='Show conversations that were generated more than once, grouped, '
                                 'with every reply the user received — the click-twice uniqueness audit')

    def handle(self, *args, **options):
        qs = AIReply.objects.order_by('-created_at')

        if options['user'] is not None:
            qs = qs.filter(user_id=options['user'])
        if options['days'] is not None:
            qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=options['days']))
        if options['type'] is not None:
            qs = qs.filter(intent_type=options['type'])
        if options['button'] is not None:
            qs = qs.filter(button_intent=options['button'])

        if options['repeats']:
            self._show_repeats(qs, options)
            return

        rows = list(qs[:options['limit']])
        if not rows:
            self.stdout.write(self.style.WARNING('No matching replies found.'))
            return

        for r in rows:
            self.stdout.write('-' * 70)
            fb = r.feedbacks.order_by('-created_at').first()
            self.stdout.write(
                f"id:{r.id}  user:{r.user_id}  type:{r.intent_type}  "
                f"button:{r.button_intent or '-'}  status:{r.status}  "
                f"user-rating:{fb.reason if fb else '-'}  "
                f"judge:{r.quality_score if r.quality_score is not None else '-'}  "
                f"created:{r.created_at}"
            )
            text = r.delivered_text or r.normalized_text or ''
            if not options['full']:
                text = text[:200]
            self.stdout.write(f"reply: {text}")
            if r.intent_type == 'specific' and r.conversation_context:
                ctx = r.conversation_context if options['full'] else r.conversation_context[:200]
                self.stdout.write(f"conversation: {ctx}")

        self.stdout.write('-' * 70)
        self.stdout.write(self.style.SUCCESS(f"Shown {len(rows)} replies."))

    def _show_repeats(self, qs, options):
        """Group left-panel replies by conversation fingerprint — every upload
        the user generated 2+ times, with each reply they got. This is the
        direct audit of the never-the-same-reply guarantee."""
        groups = (
            qs.filter(intent_type='specific', conversation_fingerprint__isnull=False)
            .values('user_id', 'conversation_fingerprint')
            .annotate(n=Count('id'))
            .filter(n__gte=2)
            .order_by('-n')[:options['limit']]
        )
        groups = list(groups)
        if not groups:
            self.stdout.write(self.style.WARNING('No repeated conversations found.'))
            return

        for g in groups:
            rows = list(
                AIReply.objects
                .filter(user_id=g['user_id'], conversation_fingerprint=g['conversation_fingerprint'])
                .order_by('created_at')
            )
            self.stdout.write('=' * 70)
            self.stdout.write(
                f"user:{g['user_id']}  generated {g['n']}x  fingerprint:{g['conversation_fingerprint'][:12]}..."
            )
            ctx = rows[0].conversation_context or rows[0].original_text or ''
            self.stdout.write(f"conversation: {ctx if options['full'] else ctx[:200]}")
            for i, r in enumerate(rows, 1):
                text = r.delivered_text or r.normalized_text or ''
                if not options['full']:
                    text = text[:200]
                self.stdout.write(f"  reply {i} ({r.created_at:%m-%d %H:%M}): {text}")

        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS(f"Shown {len(groups)} repeated conversations."))
