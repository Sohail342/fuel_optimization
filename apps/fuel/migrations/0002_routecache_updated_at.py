from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [
        ("fuel", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="routecache",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddIndex(
            model_name="routecache",
            index=models.Index(
                fields=["updated_at"], name="fuel_routec_updated_0f2a1c_idx"
            ),
        ),
    ]
