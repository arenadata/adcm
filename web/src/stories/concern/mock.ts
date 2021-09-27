import { IMPlaceholderItemType } from '../../app/models/concern/concern-reason';
import { Concern } from '../../app/models/concern/concern';

export const ISSUE_MESSAGES_FIRST_MESSAGE: Concern = {
  id: 2039,
  blocking: true,
  type: 'issue',
  reason: {
    message: 'Run ${action1} action on ${component1}.',
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

export const ISSUE_MESSAGES_SECOND_MESSAGE: Concern = {
  id: 2040,
  blocking: true,
  type: 'issue',
  reason: {
    message: 'Run the following ${action2} action on this ${component2}.',
    placeholder: {
      action2: {
        type: IMPlaceholderItemType.ComponentActionRun,
        ids : {
          cluster: 1,
          service: 2,
          component: 2,
          action: 22
        },
        name: 'Restart'
      },
      component2: {
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

export const ISSUE_MESSAGES_VERY_LONG_MESSAGE: Concern = {
  id: 2041,
  blocking: true,
  type: 'issue',
  reason: {
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

export const ISSUE_MESSAGES_LIST_MOCK = {
  concerns: [
    ISSUE_MESSAGES_FIRST_MESSAGE,
    ISSUE_MESSAGES_SECOND_MESSAGE,
    ISSUE_MESSAGES_VERY_LONG_MESSAGE,
  ],
};

export const ISSUE_MESSAGES_DEFAULT_MOCK = {
  concern: ISSUE_MESSAGES_FIRST_MESSAGE,
};

export const ISSUE_MESSAGES_VERY_LONG_MOCK = {
  concern: ISSUE_MESSAGES_VERY_LONG_MESSAGE,
};
