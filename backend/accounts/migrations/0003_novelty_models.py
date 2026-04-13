# Generated migration for novelty models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import pgvector.django


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0002_userprofile_age_userprofile_age_verified_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConversationUpload',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('original_text', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='uploads', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='AIReply',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('original_text', models.TextField()),
                ('normalized_text', models.TextField()),
                ('embedding', pgvector.django.VectorField(blank=True, dimensions=1536, null=True)),
                ('fingerprint', models.CharField(db_index=True, max_length=128)),
                ('summary', models.TextField()),
                ('intent', models.CharField(max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('status', models.CharField(db_index=True, default='pending', max_length=32)),
                ('error', models.TextField(blank=True, null=True)),
                ('upload', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='replies', to='accounts.conversationupload')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ai_replies', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='AIReplyFeedback',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.CharField(max_length=256)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reply', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='feedbacks', to='accounts.aireply')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ai_feedbacks', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(
            model_name='aireply',
            index=models.Index(fields=['user', 'created_at'], name='accounts_ai_user_id_created_idx'),
        ),
        migrations.AddIndex(
            model_name='aireply',
            index=models.Index(fields=['expires_at'], name='accounts_ai_expires_idx'),
        ),
        migrations.AddIndex(
            model_name='aireply',
            index=models.Index(fields=['fingerprint'], name='accounts_ai_fingerprint_idx'),
        ),
        migrations.AddIndex(
            model_name='aireply',
            index=models.Index(fields=['normalized_text'], name='accounts_ai_normalized_idx'),
        ),
    ]
