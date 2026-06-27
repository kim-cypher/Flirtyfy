from django.core.management.base import BaseCommand
from accounts.novelty_models import AIReply


class Command(BaseCommand):
    help = 'Show recent AI replies stored in the DB — fast inspection of what was generated/sent.'

    def add_arguments(self, parser):
        parser.add_argument('--user', type=int, default=None, help='Filter by user id')
        parser.add_argument('--limit', type=int, default=10, help='Number of replies to show (default 10)')
        parser.add_argument('--type', type=str, default=None, choices=['specific', 'button'],
                             help='specific = left panel, button = right panel')
        parser.add_argument('--button', type=str, default=None, help='Filter by button_intent (e.g. vulnerability)')
        parser.add_argument('--full', action='store_true', help='Show full text instead of truncating to 200 chars')

    def handle(self, *args, **options):
        qs = AIReply.objects.order_by('-created_at')

        if options['user'] is not None:
            qs = qs.filter(user_id=options['user'])
        if options['type'] is not None:
            qs = qs.filter(intent_type=options['type'])
        if options['button'] is not None:
            qs = qs.filter(button_intent=options['button'])

        rows = list(qs[:options['limit']])

        if not rows:
            self.stdout.write(self.style.WARNING('No matching replies found.'))
            return

        for r in rows:
            self.stdout.write('-' * 70)
            self.stdout.write(
                f"id:{r.id}  user:{r.user_id}  type:{r.intent_type}  "
                f"button:{r.button_intent or '-'}  status:{r.status}  created:{r.created_at}"
            )
            text = r.normalized_text or ''
            if not options['full']:
                text = text[:200]
            self.stdout.write(f"reply: {text}")
            if r.intent_type == 'specific' and r.conversation_context:
                ctx = r.conversation_context if options['full'] else r.conversation_context[:200]
                self.stdout.write(f"conversation: {ctx}")

        self.stdout.write('-' * 70)
        self.stdout.write(self.style.SUCCESS(f"Shown {len(rows)} replies."))
