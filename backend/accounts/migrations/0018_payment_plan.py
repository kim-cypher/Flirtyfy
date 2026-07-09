from django.db import migrations, models


class Migration(migrations.Migration):
    """Adds Payment.plan so the M-Pesa callback knows whether a completed
    payment was a one-off top-up (200 msgs) or the weekly bundle (1500 msgs,
    7-day expiry). Existing rows default to 'topup'."""

    dependencies = [
        ('accounts', '0017_merge_premium_and_quality'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='plan',
            field=models.CharField(
                max_length=20,
                choices=[('topup', 'Top-up'), ('weekly', 'Weekly')],
                default='topup',
            ),
        ),
    ]
