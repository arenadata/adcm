from django.db import models

from cm.models.base import ADCMModel, Prototype
from cm.models.types import CONFIG_FIELD_TYPE


class PrototypeConfig(ADCMModel):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)
    action = models.ForeignKey("Action", on_delete=models.CASCADE, null=True, default=None)
    name = models.CharField(max_length=160)
    subname = models.CharField(max_length=160, blank=True)
    default = models.TextField(blank=True)
    type = models.CharField(max_length=16, choices=CONFIG_FIELD_TYPE)
    display_name = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    limits = models.JSONField(default=dict)
    ui_options = models.JSONField(blank=True, default=dict)
    required = models.BooleanField(default=True)
    group_customization = models.BooleanField(null=True)

    class Meta:
        unique_together = (('prototype', 'action', 'name', 'subname'),)


class PrototypeExport(ADCMModel):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)
    name = models.CharField(max_length=160)

    class Meta:
        unique_together = (('prototype', 'name'),)


class PrototypeImport(ADCMModel):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)
    name = models.CharField(max_length=160)
    min_version = models.CharField(max_length=80)
    max_version = models.CharField(max_length=80)
    min_strict = models.BooleanField(default=False)
    max_strict = models.BooleanField(default=False)
    default = models.JSONField(null=True, default=None)
    required = models.BooleanField(default=False)
    multibind = models.BooleanField(default=False)

    class Meta:
        unique_together = (('prototype', 'name'),)