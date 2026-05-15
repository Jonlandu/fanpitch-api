from django.db import models


class Team(models.Model):
    name = models.CharField(max_length=120)
    short_name = models.CharField(max_length=16)
    country = models.CharField(max_length=80, blank=True)
    crest_url = models.URLField(blank=True)
    color_primary = models.CharField(max_length=7, default="#1e90ff")
    color_secondary = models.CharField(max_length=7, default="#ffffff")
    external_id = models.CharField(max_length=80, blank=True, db_index=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.short_name})"


class Match(models.Model):
    class Status(models.TextChoices):
        UPCOMING = "UPCOMING", "Upcoming"
        LIVE = "LIVE", "Live"
        FINISHED = "FINISHED", "Finished"

    home_team = models.ForeignKey(Team, related_name="home_matches",
                                  on_delete=models.PROTECT)
    away_team = models.ForeignKey(Team, related_name="away_matches",
                                  on_delete=models.PROTECT)
    kickoff_at = models.DateTimeField()
    status = models.CharField(max_length=10, choices=Status.choices,
                              default=Status.UPCOMING)
    home_score = models.IntegerField(default=0)
    away_score = models.IntegerField(default=0)
    competition = models.CharField(max_length=80, blank=True)
    venue = models.CharField(max_length=120, blank=True)
    source = models.CharField(max_length=20, default="SIMULATOR")
    external_id = models.CharField(max_length=80, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-kickoff_at"]
        indexes = [models.Index(fields=["status", "kickoff_at"])]

    def __str__(self) -> str:
        return f"{self.home_team.short_name} vs {self.away_team.short_name} @ {self.kickoff_at:%Y-%m-%d %H:%M}"


class MatchEvent(models.Model):
    class Type(models.TextChoices):
        KICKOFF = "KICKOFF"
        GOAL = "GOAL"
        OWN_GOAL = "OG"
        PENALTY = "PEN"
        YELLOW = "YELLOW"
        RED = "RED"
        SUB = "SUB"
        HALFTIME = "HALFTIME"
        FULLTIME = "FULLTIME"
        VAR = "VAR"
        COMMENTARY = "COMMENTARY"

    match = models.ForeignKey(Match, related_name="events",
                              on_delete=models.CASCADE)
    minute = models.IntegerField(default=0)
    type = models.CharField(max_length=12, choices=Type.choices)
    team = models.ForeignKey(Team, null=True, blank=True,
                             on_delete=models.SET_NULL)
    player_name = models.CharField(max_length=120, blank=True)
    detail = models.CharField(max_length=240, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["match", "minute", "id"]
        indexes = [models.Index(fields=["match", "minute"])]

    def __str__(self) -> str:
        return f"{self.match_id} {self.minute}' {self.type}"
