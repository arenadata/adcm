from enum import Enum

from django.db import models

PROTO_TYPE = (
    ('adcm', 'adcm'),
    ('service', 'service'),
    ('component', 'component'),
    ('cluster', 'cluster'),
    ('host', 'host'),
    ('provider', 'provider'),
)

LICENSE_STATE = (
    ('absent', 'absent'),
    ('accepted', 'accepted'),
    ('unaccepted', 'unaccepted'),
)

MONITORING_TYPE = (
    ('active', 'active'),
    ('passive', 'passive'),
)

CONFIG_FIELD_TYPE = (
    ('string', 'string'),
    ('text', 'text'),
    ('password', 'password'),
    ('secrettext', 'secrettext'),
    ('json', 'json'),
    ('integer', 'integer'),
    ('float', 'float'),
    ('option', 'option'),
    ('variant', 'variant'),
    ('boolean', 'boolean'),
    ('file', 'file'),
    ('list', 'list'),
    ('map', 'map'),
    ('structure', 'structure'),
    ('group', 'group'),
)

SCRIPT_TYPE = (
    ('ansible', 'ansible'),
    ('task_generator', 'task_generator'),
)

class PrototypeEnum(Enum):
    ADCM = 'adcm'
    Cluster = 'cluster'
    Service = 'service'
    Component = 'component'
    Provider = 'provider'
    Host = 'host'


class ConcernType(models.TextChoices):
    Lock = 'lock', 'lock'
    Issue = 'issue', 'issue'
    Flag = 'flag', 'flag'


class ActionType(models.TextChoices):
    Task = 'task', 'task'
    Job = 'job', 'job'
