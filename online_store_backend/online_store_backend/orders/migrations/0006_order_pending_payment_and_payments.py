import django.db.models.deletion
from django.db import migrations
from django.db import models


def migrate_order_statuses(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    Order.objects.filter(status="pending").update(status="pending_payment")


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0005_review_moderation_fields"),
    ]

    operations = [
        migrations.RunPython(migrate_order_statuses, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending_payment", "Pending payment"),
                    ("paid", "Paid"),
                    ("cancelled", "Cancelled"),
                ],
                default="pending_payment",
                max_length=32,
            ),
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider_id", models.CharField(max_length=64)),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "Pending"), ("succeeded", "Succeeded"), ("failed", "Failed")],
                        default="pending",
                        max_length=32,
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("currency", models.CharField(default="RUB", max_length=16)),
                ("external_id", models.CharField(blank=True, max_length=255, null=True)),
                ("payment_url", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payments",
                        to="orders.order",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["order", "status"], name="orders_paym_order_i_4513a0_idx"),
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["provider_id"], name="orders_paym_provide_226197_idx"),
        ),
    ]
