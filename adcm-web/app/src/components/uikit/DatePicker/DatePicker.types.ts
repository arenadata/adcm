import type { MouseEventHandler } from 'react';

export type MonthSwitchDirections = 'prev' | 'next';
export type CalendarMap = Date[][];

export type ChangeMonthHandler = (direction: MonthSwitchDirections) => MouseEventHandler;
export type ChangeDateHandler = (day: Date) => void;
export type SubmitDatePickerHandler = (date?: Date) => unknown;
