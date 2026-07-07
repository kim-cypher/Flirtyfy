from django.db import migrations, models


class Migration(migrations.Migration):
    """
    LLM-as-judge quality fields. quality_score is NULL until a reply has
    been judged (see the judge_replies management command), so unjudged
    rows are trivially queryable.
    """

    dependencies = [
        ('accounts', '0015_aireply_monitoring_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='aireply',
            name='quality_score',
            field=models.IntegerField(blank=True, null=True, db_index=True),
        ),
        migrations.AddField(
            model_name='aireply',
            name='quality_notes',
            field=models.TextField(blank=True, default=''),
        ),
    ]
