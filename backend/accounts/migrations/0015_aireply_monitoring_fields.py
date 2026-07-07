from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Monitoring fields for quality tracking — zero LLM cost:

    - delivered_text: the exact reply the user saw (normalized_text is lossy).
    - conversation_fingerprint: hash of the pasted conversation, so every
      reply generated for the SAME upload can be grouped, compared, and used
      as a proactive avoid-list on the next click.
    """

    dependencies = [
        ('accounts', '0014_enable_pg_trgm_extension'),
    ]

    operations = [
        migrations.AddField(
            model_name='aireply',
            name='delivered_text',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='aireply',
            name='conversation_fingerprint',
            field=models.CharField(blank=True, db_index=True, max_length=64, null=True),
        ),
    ]
