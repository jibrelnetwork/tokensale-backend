import os

from django.contrib.auth.models import User

if not User.objects.filter(username="admin").exists():
    User.objects.create_superuser("admin", "admin@example.com", os.getenv("ADMIN_PASSWORD", "Z00cVoo7eishiZ9ie94the2xe1savVah"))
