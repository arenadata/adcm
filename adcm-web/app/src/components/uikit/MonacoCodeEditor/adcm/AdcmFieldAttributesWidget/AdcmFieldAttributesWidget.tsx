import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';
import {
  type MonacoCodeEditorContentWidget,
  type IContentWidget,
  ContentWidgetPositionPreference,
  type IPosition,
  type IStandaloneCodeEditor,
} from '../../MonacoCodeEditor.types';
import type { FieldAttributes } from '@models/adcm';
import AdcmFieldAttributesWidgetContent from './AdcmFieldAttributesWidgetContent';

const widgetId = 'adcm-field-attributes-widget-id';
const domNodeId = 'adcm-field-attributes-widget-dom-id';

export class AdcmFieldAttributesWidget implements MonacoCodeEditorContentWidget {
  public type = 'content' as const;

  private widgetPosition: IPosition = { column: 1, lineNumber: 1 };
  private widgetInstance: IContentWidget | null = null;
  private editor: IStandaloneCodeEditor | null = null;

  public init(editor: IStandaloneCodeEditor) {
    this.editor = editor;
  }

  showWidget(_attributes: FieldAttributes, position: IPosition) {
    if (this.widgetInstance) {
      this.editor?.removeContentWidget(this.widgetInstance!);
    }

    this.widgetPosition = position;
    this.widgetInstance = this.getWidget();
    this.editor?.addContentWidget(this.widgetInstance);
  }

  hideWidget() {
    if (this.widgetInstance) {
      this.editor?.removeContentWidget(this.widgetInstance);
      this.widgetInstance = null;
    }
  }

  getWidget(): IContentWidget {
    return {
      getId: () => {
        return widgetId;
      },
      getDomNode: () => {
        const domNode = document.createElement('div');
        domNode.id = domNodeId;
        return domNode;
      },
      getPosition: () => {
        return {
          position: this.widgetPosition,
          preference: [ContentWidgetPositionPreference.BELOW, ContentWidgetPositionPreference.ABOVE],
        };
      },
    };
  }
  renderWidget(): ReactNode {
    const container = document.getElementById(domNodeId);
    return container && createPortal(<AdcmFieldAttributesWidgetContent />, container);
  }
}
