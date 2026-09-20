from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies=[("portal","0105_v371_receivable_credit_rules")]
    operations=[
        migrations.CreateModel(
            name="HorsePersonRelationship",
            fields=[
                ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
                ("role",models.CharField(choices=[("owner","Owner"),("co_owner","Co-owner"),("lessee","Lessee"),("contributor","Contributor")],max_length=20)),
                ("primary",models.BooleanField(default=False)),
                ("credit_recipient",models.BooleanField(default=False,help_text="Use this person for earned credits generated from the horse's use.")),
                ("start_date",models.DateField(blank=True,null=True)),
                ("end_date",models.DateField(blank=True,null=True)),
                ("active",models.BooleanField(default=True)),
                ("notes",models.CharField(blank=True,max_length=255)),
                ("created_at",models.DateTimeField(auto_now_add=True)),
                ("updated_at",models.DateTimeField(auto_now=True)),
                ("horse",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="person_relationships",to="portal.horse")),
                ("person",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="horse_relationships",to="portal.person")),
            ],
            options={"ordering":["horse__name","-primary","role","person__last_name","person__first_name"]},
        ),
        migrations.AddConstraint(model_name="horsepersonrelationship",constraint=models.UniqueConstraint(fields=("horse","person","role","start_date"),name="unique_horse_person_relationship_period")),
        migrations.AddConstraint(model_name="horsepersonrelationship",constraint=models.UniqueConstraint(condition=models.Q(("start_date__isnull",True)),fields=("horse","person","role"),name="unique_horse_person_relationship_null_start")),
        migrations.AddConstraint(model_name="horsepersonrelationship",constraint=models.UniqueConstraint(condition=models.Q(("active",True),("credit_recipient",True)),fields=("horse",),name="unique_active_horse_credit_recipient")),
    ]
