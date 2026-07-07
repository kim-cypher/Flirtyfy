"""
LLM-as-judge quality scoring — the "ask ChatGPT to rate the response"
experiment, automated, against OUR rubric, with scores stored on each reply.

Run it weekly (or nightly via cron) on delivered replies:

    python manage.py judge_replies                      # 50 newest unjudged
    python manage.py judge_replies --days 7 --limit 300
    python manage.py judge_replies --type button --button new_match
    python manage.py judge_replies --model claude-sonnet-5   # stricter judge

Cost: ~$0.001 per reply with the default Haiku judge (a 300-reply weekly
audit costs ~$0.30). Scores land in AIReply.quality_score / quality_notes,
so trends are queryable and the worst replies are findable instantly.
"""
import json
import re
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Avg
from django.utils import timezone

from accounts.novelty_models import AIReply


# The rubric is the product owner's own quality definition, made gradeable.
JUDGE_SYSTEM = (
    "You are a strict quality judge for a dating-platform reply-writing system. "
    "You will be given a reply a woman sent to a man (and, when available, the "
    "conversation it responds to). Score how likely this reply is to make him "
    "feel seen, chosen, and special — and to make him answer immediately.\n\n"
    "Score 1-10 against ALL of these:\n"
    "1. SEEN: does it respond to something specific about HIM (his words, his "
    "life, his vibe), or could it be sent to any man? Generic = low.\n"
    "2. QUESTION: is the final question a real, complete, interesting question "
    "about him — impossible to answer yes/no, easy and tempting to answer?\n"
    "3. REGISTER: does it match his energy (never more sexual than he was; "
    "warm when he is friendly)?\n"
    "4. HUMAN: does it read like a real woman texting — plain words, natural "
    "rhythm — not like AI (no formulas, no purple prose, no meta-commentary)?\n"
    "5. AUTOMATIC FAIL (score 3 or less) if it: mentions meeting/calling/"
    "distances/locations/schedules; names a day of the week or clock time; "
    "references a memory or physical moment they never shared; quotes something "
    "he never said; is incomplete or ends in a fake question (a statement with "
    "a question mark); breaks character in any way.\n\n"
    "Output ONLY this JSON on one line:\n"
    "{\"score\": <1-10>, \"notes\": \"<one or two short sentences: the main "
    "strength and the main weakness>\"}"
)


class Command(BaseCommand):
    help = 'Score delivered replies 1-10 with an LLM judge; stores results on each AIReply.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=50, help='Max replies to judge this run (default 50)')
        parser.add_argument('--days', type=int, default=7, help='Only replies from the last N days (default 7)')
        parser.add_argument('--user', type=int, default=None, help='Filter by user id')
        parser.add_argument('--type', type=str, default=None, choices=['specific', 'button'])
        parser.add_argument('--button', type=str, default=None, help='Filter by button_intent')
        parser.add_argument('--rejudge', action='store_true', help='Also re-score replies that already have a score')
        parser.add_argument('--model', type=str, default=None,
                            help='Judge model (default: ANTHROPIC_REWRITE_MODEL, i.e. Haiku — cheap; '
                                 'use claude-sonnet-5 for a stricter judge)')

    def handle(self, *args, **options):
        from accounts.services.button_generator import get_anthropic_client

        model = options['model'] or getattr(settings, 'ANTHROPIC_REWRITE_MODEL', 'claude-haiku-4-5')

        qs = (
            AIReply.objects
            .exclude(delivered_text='')
            .filter(created_at__gte=timezone.now() - timedelta(days=options['days']))
            .order_by('-created_at')
        )
        if not options['rejudge']:
            qs = qs.filter(quality_score__isnull=True)
        if options['user'] is not None:
            qs = qs.filter(user_id=options['user'])
        if options['type'] is not None:
            qs = qs.filter(intent_type=options['type'])
        if options['button'] is not None:
            qs = qs.filter(button_intent=options['button'])

        rows = list(qs[:options['limit']])
        if not rows:
            self.stdout.write(self.style.WARNING('Nothing to judge.'))
            return

        client = get_anthropic_client()
        judged, failed = 0, 0

        for r in rows:
            if r.intent_type == 'specific' and r.conversation_context:
                ctx = r.conversation_context[-1200:]
                user_msg = (
                    f"CONVERSATION (he wrote the last message):\n{ctx}\n\n"
                    f"HER REPLY TO JUDGE:\n{r.delivered_text}"
                )
            else:
                user_msg = (
                    f"CONTEXT: standalone message sent from the '{r.button_intent or 'unknown'}' "
                    f"scenario button (no conversation visible).\n\n"
                    f"HER MESSAGE TO JUDGE:\n{r.delivered_text}"
                )
            try:
                resp = client.messages.create(
                    model=model,
                    system=JUDGE_SYSTEM,
                    messages=[{'role': 'user', 'content': user_msg}],
                    max_tokens=120,
                )
                raw = next((b.text for b in resp.content if getattr(b, 'type', '') == 'text'), '').strip()
                score, notes = self._parse(raw)
                if score is None:
                    failed += 1
                    continue
                r.quality_score = score
                r.quality_notes = notes[:500]
                r.save(update_fields=['quality_score', 'quality_notes'])
                judged += 1
            except Exception as e:
                self.stderr.write(f"judge failed for reply {r.id}: {e}")
                failed += 1

        self._summary(options, judged, failed)

    @staticmethod
    def _parse(raw):
        raw = raw.strip()
        if raw.startswith('```'):
            raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw, flags=re.DOTALL).strip()
        try:
            data = json.loads(raw)
            score = int(data.get('score'))
            if 1 <= score <= 10:
                return score, str(data.get('notes', '')).strip()
        except (json.JSONDecodeError, TypeError, ValueError):
            m = re.search(r'"score"\s*:\s*(\d+)', raw)
            if m and 1 <= int(m.group(1)) <= 10:
                n = re.search(r'"notes"\s*:\s*"((?:[^"\\]|\\.)*)"', raw)
                return int(m.group(1)), (n.group(1) if n else '')
        return None, None

    def _summary(self, options, judged, failed):
        base = AIReply.objects.filter(
            quality_score__isnull=False,
            created_at__gte=timezone.now() - timedelta(days=options['days']),
        )
        if options['type']:
            base = base.filter(intent_type=options['type'])

        avg = base.aggregate(a=Avg('quality_score'))['a']
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS(
            f"Judged {judged} replies this run ({failed} failed). "
            f"Average score (last {options['days']}d, all judged): "
            f"{avg:.1f}/10" if avg is not None else f"Judged {judged} replies."
        ))
        self.stdout.write("\nScore distribution:")
        for s in range(10, 0, -1):
            n = base.filter(quality_score=s).count()
            if n:
                self.stdout.write(f"  {s:>2}: {'#' * min(n, 60)} {n}")

        worst = list(base.order_by('quality_score', '-created_at')[:5])
        if worst:
            self.stdout.write("\nWorst 5 (fix material for the week):")
            for r in worst:
                self.stdout.write('-' * 70)
                self.stdout.write(
                    f"score:{r.quality_score}  id:{r.id}  type:{r.intent_type}  "
                    f"button:{r.button_intent or '-'}"
                )
                self.stdout.write(f"reply: {(r.delivered_text or '')[:180]}")
                self.stdout.write(f"judge: {r.quality_notes[:180]}")
        self.stdout.write('=' * 70)
