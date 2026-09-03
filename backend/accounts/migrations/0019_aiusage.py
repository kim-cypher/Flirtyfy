from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0018_payment_plan'),
    ]

    operations = [
        migrations.CreateModel(
            name='AIUsage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('label', models.CharField(help_text='LEFT_PANEL, BUTTON_MAIN, WARMUP, DEDUP_*, ...', max_length=32)),
                ('model', models.CharField(max_length=64)),
                ('input_tokens', models.IntegerField(default=0)),
                ('output_tokens', models.IntegerField(default=0)),
                ('cache_read_tokens', models.IntegerField(default=0)),
                ('cache_write_tokens', models.IntegerField(default=0)),
                ('cost_usd', models.DecimalField(decimal_places=6, default=0, max_digits=12)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ai_usage', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'AI Usage',
                'verbose_name_plural': 'AI Usage',
            },
        ),
        migrations.AddIndex(
            model_name='aiusage',
            index=models.Index(fields=['created_at'], name='aiusage_created_idx'),
        ),
        migrations.AddIndex(
            model_name='aiusage',
            index=models.Index(fields=['user', 'created_at'], name='aiusage_user_created_idx'),
        ),
        migrations.AddIndex(
            model_name='aiusage',
            index=models.Index(fields=['label', 'created_at'], name='aiusage_label_created_idx'),
        ),
    ]
