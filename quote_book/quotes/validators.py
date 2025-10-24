from datetime import date

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


def validate_date(value):
    if value > date.today():
        raise ValidationError(_("Date in the future"), code="invalid")
