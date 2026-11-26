import type React from 'react';
import { useMemo } from 'react';
import type { ErrorNotification } from '@models/notification';
import Alert from './Alert';
import type { AlertOptions } from './Alert.types';

import s from './Alert.module.scss';
import type { HTMLReactParserOptions } from 'html-react-parser';
import parse, { Element } from 'html-react-parser';
import { sanitizeErrorAlertHtml } from './ErrorAlert.utils';

const ErrorAlert: React.FC<ErrorNotification & AlertOptions> = ({ model: { message }, onClose }) => {
  const parsedMessage = useMemo(() => {
    if (!message) return null;

    const sanitizedMessage = sanitizeErrorAlertHtml(message);

    const parseOptions: HTMLReactParserOptions = {
      replace: (domNode) => {
        if (domNode instanceof Element && domNode.attribs && domNode.name === 'a') {
          const existingClass = domNode.attribs.class ?? '';
          domNode.attribs.class = [existingClass, 'text-link'].filter(Boolean).join(' ');
        }
        return domNode;
      },
    };

    return parse(sanitizedMessage, parseOptions);
  }, [message]);

  return (
    <Alert icon="triangle-alert" className={s.alert_error} onClose={onClose}>
      {parsedMessage}
    </Alert>
  );
};

export default ErrorAlert;
