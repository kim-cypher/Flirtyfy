# Reconciles pre-existing model drift: help_text on two AIReply fields was
# edited without a migration. help_text-only AlterField = no real DB change;
# this just brings migration state in line with the model.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0019_aiusage'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aireply',
            name='conversation_fingerprint',
            field=models.CharField(blank=True, db_index=True, help_text='SHA-256 of the normalized pasted conversation — groups every reply generated for the same upload', max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='aireply',
            name='delivered_text',
            field=models.TextField(blank=True, default='', help_text='The exact reply text shown to the user (normalized_text is lossy — lowercased, punctuation stripped)'),
        ),
    ]
