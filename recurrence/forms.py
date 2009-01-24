from django import forms
from django.conf import settings
from django.utils import safestring, simplejson
from django.utils.translation import ugettext_lazy as _

import recurrence


class RecurrenceWidget(forms.Textarea):
    def __init__(self, attrs=None, **kwargs):
        self.js_widget_options = kwargs
        defaults = {'class': 'recurrence-widget'}
        if attrs is not None:
            defaults.update(attrs)
        super(RecurrenceWidget, self).__init__(defaults)
        
    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        elif isinstance(value, recurrence.Recurrence):
            value = recurrence.serialize(value)

        widget_init_js = (
            '<script type="text/javascript">'
            'new recurrence.widget.Widget(\'%s\', %s);'
            '</script>'
        ) % (attrs['id'], simplejson.dumps(self.js_widget_options))

        return safestring.mark_safe(u'%s\n%s' % (
            super(RecurrenceWidget, self).render(name, value, attrs),
            widget_init_js))

    def get_media(self):
        media_prefix = getattr(settings, 'RECURRENCE_MEDIA_PREFIX', '/')
        return forms.Media(
            js=(
                media_prefix + 'js/recurrence.js',
                media_prefix + 'js/widget.js',
            ),
            css={
                'all': (
                    media_prefix + 'css/recurrence.css',
                ),
            },
        )
    media = property(get_media)


class RecurrenceField(forms.CharField):
    """
    A Field that accepts the recurrence related parameters of rfc2445.

    Values are deserialized into `recurrence.base.Recurrence` objects.
    """
    widget = RecurrenceWidget
    default_error_messages = {
        'invalid_freqency': _(
            u'Invalid frequency.'),
        'max_rrules_exceeded': _(
            u'Max rules exceeded. The limit is %(limit)s'),
        'max_exrules_exceeded': _(
            u'Max exclusion rules exceeded. The limit is %(limit)s'),
        'max_rdates_exceeded': _(
            u'Max dates exceeded. The limit is %(limit)s'),
        'max_exdates_exceeded': _(
            u'Max exclusion dates exceeded. The limit is %(limit)s'),
    }

    def __init__(
        self,
        frequencies=None, accept_dtstart=True, accept_dtend=True,
        max_rrules=None, max_exrules=None, max_rdates=None, max_exdates=None,
        *args, **kwargs):
        """
        Create a recurrence field.

        A `RecurrenceField` takes the same parameters as a `CharField`
        field with some additional paramaters.

        :Parameters:
            `frequencies` : sequence
                A sequence of the frequency constants specifying which
                frequencies are valid for input. By default all
                frequencies are valid.

            `accept_dtstart` : bool
                Whether to accept a dtstart value passed in the input.

            `accept_dtend` : bool
                Whether to accept a dtend value passed in the input.

            `max_rrules` : int
                The max number of rrules to accept in the input. A
                value of ``0`` means input of rrules is disabled.

            `max_exrules` : int
                The max number of exrules to accept in the input. A
                value of ``0`` means input of exrules is disabled.

            `max_rdates` : int
                The max number of rdates to accept in the input. A
                value of ``0`` means input of rdates is disabled.

            `max_exdates` : int
                The max number of exdates to accept in the input. A
                value of ``0`` means input of exdates is disabled.
        """
        self.accept_dtstart = accept_dtstart
        self.accept_dtend = accept_dtend
        self.max_rrules = max_rrules
        self.max_exrules = max_exrules
        self.max_rdates = max_rdates
        self.max_exdates = max_exdates
        if frequencies is not None:
            self.frequencies = frequencies
        else:
            self.frequencies = (
                recurrence.YEARLY, recurrence.MONTHLY,
                recurrence.WEEKLY, recurrence.DAILY,
                recurrence.HOURLY, recurrence.MINUTELY,
                recurrence.SECONDLY,
            )
        super(RecurrenceField, self).__init__(*args, **kwargs)

    def clean(self, value):
        """
        Validates that ``value`` deserialized into a
        `recurrence.base.Recurrence` object falls within the
        parameters specified to the `RecurrenceField` constructor.
        """
        recurrence_obj = recurrence.deserialize(value)

        if not self.accept_dtstart:
            recurrence_obj.dtstart = None
        if not self.accept_dtend:
            recurrence_obj.dtend = None

        if self.max_rrules is not None:
            if len(recurrence_obj.rrules) > self.max_rrules:
                raise forms.ValidationError(
                    self.error_messages['max_rrules_exceeded'] % {
                    'limit': self.max_rrules})
        if self.max_exrules is not None:
            if len(recurrence_obj.exrules) > self.max_exrules:
                raise forms.ValidationError(
                    self.error_messages['max_exrules_exceeded'] % {
                    'limit': self.max_exrules})
        if self.max_rdates is not None:
            if len(recurrence_obj.rdates) > self.max_rdates:
                raise forms.ValidationError(
                    self.error_messages['max_rdates_exceeded'] % {
                    'limit': self.max_rdates})
        if self.max_exdates is not None:
            if len(recurrence_obj.exdates) > self.max_exdates:
                raise forms.ValidationError(
                    self.error_messages['max_exdates_exceeded'] % {
                    'limit': self.max_exdates})

        for rrule in recurrence_obj.rrules:
            if rrule.freq not in self.frequencies:
                raise forms.ValidationError(
                    self.error_messages['invalid_frequency'])
        for exrule in recurrence_obj.exrules:
            if exrule.freq not in self.frequencies:
                raise forms.ValidationError(
                    self.error_messages['invalid_frequency'])

        return recurrence_obj
