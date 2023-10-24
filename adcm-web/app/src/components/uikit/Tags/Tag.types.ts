import React from 'react';

export interface TagOptions {
  endAdornment?: React.ReactNode;
  startAdornment?: React.ReactNode;
  isDisabled?: boolean;
  variant?: 'primary' | 'secondary';
}
