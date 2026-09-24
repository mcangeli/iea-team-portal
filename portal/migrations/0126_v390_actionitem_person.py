from django.db import migrations, models
import django.db.models.deletion


def backfill_action_item_people(apps, schema_editor):
    ActionItem = apps.get_model("portal", "ActionItem")
    LegacyPersonLink = apps.get_model("portal", "LegacyPersonLink")
    links = dict(
        LegacyPersonLink.objects.exclude(rider_id=None).values_list("rider_id", "person_id")
    )
    for item in ActionItem.objects.filter(person_id=None).exclude(rider_id=None).iterator():
        person_id = links.get(item.rider_id)
        if person_id:
            ActionItem.objects.filter(pk=item.pk).update(person_id=person_id)


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0125_v390_volunteer_person"),
    ]

    operations = [
        migrations.AddField(
            model_name="actionitem",
            name="person",
            field=models.ForeignKey(
                blank=True,
                help_text="Canonical participant for this action item. Rider is retained only for compatibility.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="action_items",
                to="portal.person",
            ),
        ),
        migrations.RunPython(backfill_action_item_people, migrations.RunPython.noop),
    ]
