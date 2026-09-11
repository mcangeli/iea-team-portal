import re
from collections import Counter

from django.db import migrations, models


def backfill_class_codes(apps, schema_editor):
    SeasonClass = apps.get_model("portal", "SeasonClass")
    ShowClass = apps.get_model("portal", "ShowClass")

    for season_class in SeasonClass.objects.all().iterator():
        values = [
            (value or "").strip().upper()
            for value in ShowClass.objects.filter(season_class_id=season_class.pk)
            .exclude(class_number="")
            .values_list("class_number", flat=True)
        ]
        values = [value for value in values if value]
        code = Counter(values).most_common(1)[0][0] if values else ""
        if not code:
            match = re.match(r"^([A-Z]+\d+[A-Z]?)\b", (season_class.name or "").strip().upper())
            code = match.group(1) if match else ""
        if code:
            SeasonClass.objects.filter(pk=season_class.pk).update(class_code=code)
            ShowClass.objects.filter(season_class_id=season_class.pk, class_number="").update(class_number=code)


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0037_v212_hoofprint_snapshots"),
    ]

    operations = [
        migrations.AddField(
            model_name="seasonclass",
            name="class_code",
            field=models.CharField(
                blank=True,
                help_text="Short IEA class identifier, such as H1, H2, H8, or H14.",
                max_length=30,
            ),
        ),
        migrations.RunPython(backfill_class_codes, migrations.RunPython.noop),
    ]
