from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="IntegrationConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "kind",
                    models.CharField(
                        choices=[("payment", "Payment"), ("shipping", "Shipping")],
                        max_length=32,
                    ),
                ),
                ("provider_id", models.CharField(max_length=64)),
                ("enabled", models.BooleanField(default=False)),
                ("is_sandbox", models.BooleanField(default=True)),
                ("display_name", models.CharField(blank=True, default="", max_length=255)),
                ("credentials", models.JSONField(blank=True, default=dict)),
                ("settings", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("kind", "provider_id"),
                        name="uniq_kind_provider",
                    )
                ]
            },
        )
    ]
