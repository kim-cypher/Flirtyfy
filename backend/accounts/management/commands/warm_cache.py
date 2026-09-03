"""
Idle-aware persona-cache warmer. Schedule on the host with cron, e.g. every 5m:

    */5 * * * * docker exec flirty-backend python manage.py warm_cache >> /var/log/flirty-warm.log 2>&1

Fires a single tiny prefill ONLY when the persona cache is close to its 1h TTL
(i.e. no real left-panel generation happened in the last ~45 min). During busy
hours real traffic keeps the stamp fresh and this is a no-op. Running inside the
backend container guarantees it uses the same ANTHROPIC_FAST_MODEL as real
requests, so it warms the exact cache entry they read.
"""
from django.core.management.base import BaseCommand

from accounts.services.cache_warmer import (
    seconds_since_touch, warm_now, _REFRESH_AFTER_SECONDS,
)


class Command(BaseCommand):
    help = 'Keep the persona prompt cache warm during idle periods (idle-aware).'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Warm immediately regardless of idle time (testing).')

    def handle(self, *args, **options):
        from accounts.services.button_generator import get_anthropic_client

        idle = seconds_since_touch()
        if not options['force'] and idle is not None and idle < _REFRESH_AFTER_SECONDS:
            self.stdout.write(
                f"skip: persona cache touched {int(idle)}s ago "
                f"(threshold {_REFRESH_AFTER_SECONDS}s)"
            )
            return

        if warm_now(get_anthropic_client()):
            why = 'forced' if options['force'] else (
                f'idle {int(idle)}s' if idle is not None else 'no prior activity'
            )
            self.stdout.write(f"warmed persona cache ({why})")
        else:
            self.stderr.write("warm ping failed (see logs)")
