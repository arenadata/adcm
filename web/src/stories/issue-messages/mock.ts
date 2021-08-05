import { IMPlaceholderItemType } from '../../app/models/issue-message';

export const ISSUE_MESSAGES_DEFAULT_MOCK = {
  message: {
    message: 'Run ${action1} action on ${component1}.',
    id: 2039,
    placeholder: {
      action1: {
        type: IMPlaceholderItemType.ComponentActionRun,
        ids : {
          cluster: 1,
          service: 2,
          component: 2,
          action: 22
        },
        name: 'Restart'
      },
      component1: {
        type: IMPlaceholderItemType.ComponentConfig,
        ids : {
          cluster: 1,
          service: 2,
          component: 2
        },
        name: 'My Component'
      }
    }
  }
};

export const ISSUE_MESSAGES_VERY_LONG_MOCK = {
  message: {
    message: 'Run ${action1} action on ${component1}. This is a very very very very very very very very very very very very' +
      ' very very very very very very very very very very very very very very very very very very very very very very very' +
      ' very very very very very very very very very very very very very very very very very very very very very very very' +
      ' very very very very very very very very very very very very very very very very very very very very very very very' +
      ' very very very very very very very very very very very very very very very very very very very very very very very' +
      ' very very very very very very very very very very very very very very very very very very very very very very very' +
      ' very very very very very very very very very very very very very very very very very very very very very very very' +
      ' very very very very very very very very very very very very very very very very very very very very very very very' +
      ' very very very very very very very very very very very very very very very very very very very very very very very' +
      ' very very very very very very very very very very very very very very very very very very very very very very very' +
      ' very very very very very very very very very very very very very very very very very very very very very very very' +
      ' long message. Bonus ${action2}!',
    id: 2039,
    placeholder: {
      action1: {
        type: IMPlaceholderItemType.ComponentActionRun,
        ids : {
          cluster: 1,
          service: 2,
          component: 2,
          action: 22
        },
        name: 'Restart'
      },
      component1: {
        type: IMPlaceholderItemType.ComponentConfig,
        ids : {
          cluster: 1,
          service: 2,
          component: 2
        },
        name: 'My Component'
      },
      action2: {
        type: IMPlaceholderItemType.ComponentActionRun,
        ids: {
          cluster: 1,
          service: 2,
          component: 2,
          action: 22
        },
        name: ''
      }
    }
  }
};
