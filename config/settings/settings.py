import os


settings_module = os.environ.get(
    "DJANGO_SETTINGS_MODULE", "config.settings.developement"
)

if settings_module.endswith("production"):
    from .production import *  # noqa
else:
    from .developement import *  # noqa
