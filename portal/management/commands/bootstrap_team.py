from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from portal.models import Team, Season, UserProfile
from datetime import date
class Command(BaseCommand):
    help="Create the first team, active season and administrator account"
    def add_arguments(self,p):
        p.add_argument("--team",required=True); p.add_argument("--season",required=True); p.add_argument("--username",required=True); p.add_argument("--email",required=True); p.add_argument("--password",required=True)
    def handle(self,*args,**o):
        if User.objects.filter(username=o["username"]).exists(): raise CommandError("Username already exists")
        team,_=Team.objects.get_or_create(name=o["team"],defaults={"short_name":o["team"]})
        season,_=Season.objects.get_or_create(team=team,name=o["season"],defaults={"start_date":date.today(),"end_date":date(date.today().year+1,7,31),"is_active":True})
        Team.objects.filter(pk=team.pk); team.seasons.exclude(pk=season.pk).update(is_active=False); season.is_active=True; season.save()
        u=User.objects.create_superuser(o["username"],o["email"],o["password"]); u.profile.team=team; u.profile.role=UserProfile.Role.ADMIN; u.profile.save()
        self.stdout.write(self.style.SUCCESS(f"Created {team} / {season.name} / {u.username}"))
