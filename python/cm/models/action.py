from django.db import models

from cm.models.base import AbstractAction, AbstractSubAction, ADCMEntity, Prototype


class Action(AbstractAction):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)

    __error_code__ = 'ACTION_NOT_FOUND'

    @property
    def prototype_name(self):
        return self.prototype.name

    @property
    def prototype_version(self):
        return self.prototype.version

    @property
    def prototype_type(self):
        return self.prototype.type

    def get_id_chain(self, target_ids: dict) -> dict:
        """Get action ID chain for front-end URL generation in message templates"""
        target_ids['action'] = self.pk
        result = {
            'type': self.prototype.type + '_action_run',
            'name': self.display_name or self.name,
            'ids': target_ids,
        }
        return result

    def allowed(self, obj: ADCMEntity) -> bool:
        """Check if action is allowed to be run on object"""
        if self.state_unavailable == 'any' or self.multi_state_unavailable == 'any':
            return False

        if isinstance(self.state_unavailable, list) and obj.state in self.state_unavailable:
            return False

        if isinstance(self.multi_state_unavailable, list) and obj.has_multi_state_intersection(
            self.multi_state_unavailable
        ):
            return False

        state_allowed = False
        if self.state_available == 'any':
            state_allowed = True
        elif isinstance(self.state_available, list) and obj.state in self.state_available:
            state_allowed = True

        multi_state_allowed = False
        if self.multi_state_available == 'any':
            multi_state_allowed = True
        elif isinstance(self.multi_state_available, list) and obj.has_multi_state_intersection(
            self.multi_state_available
        ):
            multi_state_allowed = True

        return state_allowed and multi_state_allowed


class SubAction(AbstractSubAction):
    action = models.ForeignKey(Action, on_delete=models.CASCADE)