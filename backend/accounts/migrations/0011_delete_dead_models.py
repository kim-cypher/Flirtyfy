from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_aireply_content_fingerprint'),
    ]

    operations = [
        # ResponseLog first — it has a FK to ConversationLog
        migrations.DeleteModel(name='ResponseLog'),
        migrations.DeleteModel(name='ConversationLog'),
        migrations.DeleteModel(name='NgramLog'),
        migrations.DeleteModel(name='VocabCooldown'),
    ]
