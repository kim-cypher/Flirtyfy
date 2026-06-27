from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_aireply_button_intent_aireply_conversation_context_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='aireply',
            name='content_fingerprint',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='SHA-256 of intent template key — detects same question in different words',
                max_length=128,
                null=True,
            ),
        ),
    ]
