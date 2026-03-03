from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0010_orderitem_unit_price_and_product_view_event"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="delivery_external_id",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="delivery_last_event_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="delivery_last_payload",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="delivery_status",
            field=models.CharField(
                choices=[
                    ("awaiting_payment", "Awaiting payment"),
                    ("ready_for_dispatch", "Ready for dispatch"),
                    ("handover_to_delivery", "Handed over to delivery"),
                    ("in_transit", "In transit"),
                    ("ready_for_pickup", "Ready for pickup"),
                    ("delivered", "Delivered"),
                    ("delivery_failed", "Delivery failed"),
                    ("cancelled", "Cancelled"),
                ],
                default="awaiting_payment",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="delivery_status_note",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="order",
            name="delivery_tracking_number",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
    ]
