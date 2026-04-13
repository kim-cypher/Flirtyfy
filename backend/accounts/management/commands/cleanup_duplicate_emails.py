from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from collections import defaultdict


class Command(BaseCommand):
    help = 'Clean up duplicate users with the same email address'

    def handle(self, *args, **options):
        # Group users by email
        email_groups = defaultdict(list)
        for user in User.objects.all().order_by('-date_joined'):
            email_groups[user.email].append(user)

        # Find duplicates
        duplicates = {email: users for email, users in email_groups.items() if len(users) > 1}

        if not duplicates:
            self.stdout.write(self.style.SUCCESS('No duplicate emails found.'))
            return

        self.stdout.write(self.style.WARNING(f'Found {len(duplicates)} email addresses with duplicates:'))

        for email, users in duplicates.items():
            self.stdout.write(f'\nEmail: {email}')
            self.stdout.write(f'  Total users: {len(users)}')
            
            # Keep the most recent (first in list due to order_by('-date_joined'))
            keep_user = users[0]
            delete_users = users[1:]
            
            self.stdout.write(f'  Keeping user ID {keep_user.id} (created {keep_user.date_joined})')
            
            for user in delete_users:
                self.stdout.write(f'  Deleting user ID {user.id} (created {user.date_joined})')
                user.delete()
            
            self.stdout.write(self.style.SUCCESS(f'  ✓ Deleted {len(delete_users)} duplicate(s)'))

        self.stdout.write(self.style.SUCCESS('\nDuplicate email cleanup completed.'))
