from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from datetime import date


def validate_date(value):
    if value > date.today():
        raise ValidationError(_("Date in the future"), code="invalid")
