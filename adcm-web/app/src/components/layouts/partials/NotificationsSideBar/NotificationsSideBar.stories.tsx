import type React from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import Alert from '@layouts/partials/NotificationsSideBar/Alert/Alert';
import { store } from '@store';
import { Provider } from 'react-redux';
import Button from '@uikit/Button/Button';
import { useDispatch } from '@hooks';
import { showError, showInfo, showSuccess } from '@store/notificationsSlice';
import NotificationsSideBar from '@layouts/partials/NotificationsSideBar/NotificationsSideBar';

type Story = StoryObj<typeof Alert>;

export default {
  title: 'uikit/Notifications',
  component: Alert,
  decorators: [
    (Story) => {
      return (
        <Provider store={store}>
          <Story />
          <NotificationsSideBar />
        </Provider>
      );
    },
  ],
  argTypes: {
    children: {
      table: {
        disable: true,
      },
    },
  },
} as Meta<typeof Alert>;

export const Notification: Story = {
  render: () => {
    return <NotificationSidebarExample />;
  },
};

const NotificationSidebarExample: React.FC = () => {
  const dispatch = useDispatch();

  return (
    <div style={{ display: 'flex', gap: 30 }}>
      <Button
        onClick={() => {
          dispatch(
            showInfo({
              message: 'Some Info text',
            }),
          );
        }}
      >
        Show info notification
      </Button>
      <Button
        onClick={() => {
          dispatch(
            showError({
              message: 'Some errors text',
            }),
          );
        }}
      >
        Show error notification
      </Button>
      <Button
        onClick={() => {
          dispatch(
            showSuccess({
              message: 'Some success text',
            }),
          );
        }}
      >
        Show success notification
      </Button>
    </div>
  );
};
