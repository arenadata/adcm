import { ComponentRef, Type } from '@angular/core';
import { MatCheckboxChange } from '@angular/material/checkbox';

export interface RowEventData {
  row: any;
  event: MouseEvent;
}

export interface ChoiceEventData<T> {
  row: T;
  event: MatCheckboxChange;
}

export interface IListResult<T> {
  count: number;
  next: string;
  previous: string;
  results: T[];
}

/**
 * Describing complex columns
 */
export interface IColumnDescription {
  label?: string;
  type?: 'buttons' | 'date' | 'link' | 'dynamic-column' | 'component' | 'choice';
  className?: string;
  headerClassName?: string;
  guid?: string;
}

export interface ISortableColumn<T> extends IColumnDescription {
  sort?: string;
}

export type CellValueType = string | number;

export type ValueFunc<T> = (row: T) => CellValueType;
export interface IValueColumn<T> extends ISortableColumn<T> {
  value: ValueFunc<T>;
}

export type DisabledCheckboxFunc<T> = (row: T) => boolean;

export interface IDateColumn<T> extends IValueColumn<T> {
  type: 'date';
}

export type ButtonCallback<T> = (row: T, event: MouseEvent) => void;
export interface IButton<T> {
  icon?: string;
  callback: ButtonCallback<T>;
  tooltip?: string;
}

export interface IButtonsColumn<T> extends IColumnDescription {
  type: 'buttons';
  buttons: IButton<T>[];
}

export interface IChoiceColumn<T> extends IColumnDescription {
  type: 'choice';
  modelKey: string;
  disabled?: DisabledCheckboxFunc<T>;
}

export type UrlColumnFunc<T> = (row: T) => string;
export interface ILinkColumn<T> extends IValueColumn<T> {
  type: 'link';
  url: UrlColumnFunc<T>;
}

export interface AdwpComponentHolder<T> {
  row: T;
}

export interface AdwpCellComponent<T> extends AdwpComponentHolder<T> {
  column?: IColumn<T>;
}

export type AdwpCellComponentType<T> = Type<AdwpCellComponent<T>>;
export type AdwpRowComponentType<T> = Type<AdwpRowComponentType<T>>;

export type InstanceTakenFunc<T> = (componentRef: ComponentRef<AdwpCellComponent<T>>) => void;

export interface IComponentColumn<T> extends ISortableColumn<T> {
  type: 'component';
  component: AdwpCellComponentType<T>;
  instanceTaken?: InstanceTakenFunc<T>;
}

export interface ICell {
  cssClass: string;
  value: CellValueType;
}

export type DynamicColumnFunc<T> = (row: T) => ICell;

export interface IDynamicColumn<T> extends ISortableColumn<T> {
  type: 'dynamic-column';
  handle: DynamicColumnFunc<T>;
}

export type IColumn<T> =
  IValueColumn<T>
  | IDateColumn<T>
  | IButtonsColumn<T>
  | ILinkColumn<T>
  | IDynamicColumn<T>
  | IComponentColumn<T>
  | IChoiceColumn<T>;

export type IColumns<T> = Array<IColumn<T>>;
