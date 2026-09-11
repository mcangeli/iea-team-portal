from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0009_v160_communications_privacy"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CommitteeAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("upper_parent","Upper Team Parent"),("futures_parent","Futures Team Parent"),("treasurer","Treasurer"),("points_secretary","Secretary / Points Secretary")], max_length=30)),
                ("active", models.BooleanField(default=True)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("season", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="committee_assignments", to="portal.season")),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="committee_assignments", to="portal.team")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="committee_assignments", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering":["role","user__last_name","user__first_name"]},
        ),
        migrations.AddConstraint(model_name="committeeassignment", constraint=models.UniqueConstraint(fields=("season","user","role"), name="unique_committee_assignment")),
        migrations.CreateModel(
            name="ShowLeadAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("active", models.BooleanField(default=True)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("show", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lead_assignments", to="portal.show")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="show_lead_assignments", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering":["user__last_name","user__first_name"]},
        ),
        migrations.AddConstraint(model_name="showleadassignment", constraint=models.UniqueConstraint(fields=("show","user"), name="unique_show_lead_assignment")),
        migrations.CreateModel(
            name="ShowPlanningItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("category", models.CharField(choices=[("lunch","Lunch"),("snack","Snack"),("drink","Drink"),("supply","Supply"),("task","Show-day task"),("other","Other")], default="task", max_length=20)),
                ("title", models.CharField(max_length=160)),
                ("quantity", models.CharField(blank=True, max_length=60)),
                ("details", models.CharField(blank=True, max_length=255)),
                ("completed", models.BooleanField(default=False)),
                ("family_visible", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("assigned_to", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="show_planning_items", to=settings.AUTH_USER_MODEL)),
                ("claimed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="claimed_show_planning_items", to=settings.AUTH_USER_MODEL)),
                ("show", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="planning_items", to="portal.show")),
            ],
            options={"ordering":["sort_order","category","title"]},
        ),
    ]
