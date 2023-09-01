import React from 'react';

export interface TabButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  isActive?: boolean;
}

export interface TabProps extends React.HTMLAttributes<HTMLAnchorElement> {
  to: string;
  subPattern?: string;
  disabled?: boolean;
  isActive?: boolean;
}
