import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';
import {
  type MonacoCodeEditorOverlayWidget,
  OverlayWidgetPositionPreference,
  type ILayoutWidget,
  type IStandaloneCodeEditor,
} from '../MonacoCodeEditor.types';
import MarkersWidgetContent from './MarkersWidgetContent';

const widgetId = 'markers-widget-id';
const domNodeId = 'markers-widget-dom-id';

export class MarkersWidget implements MonacoCodeEditorOverlayWidget {
  public type = 'overlay' as const;

  private widgetInstance: ILayoutWidget | null = null;
  private editor: IStandaloneCodeEditor | null = null;

  public init(editor: IStandaloneCodeEditor) {
    this.editor = editor;
  }

  showWidget() {
    if (this.widgetInstance) {
      this.editor?.removeOverlayWidget(this.widgetInstance!);
    }

    this.widgetInstance = this.getWidget();
    this.editor?.addOverlayWidget(this.widgetInstance);
  }

  hideWidget() {
    this.editor?.removeOverlayWidget(this.widgetInstance!);
    this.widgetInstance = null;
  }

  getWidget(): ILayoutWidget {
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
          preference: OverlayWidgetPositionPreference.TOP_RIGHT_CORNER,
        };
      },
    };
  }
  renderWidget(): ReactNode {
    const container = document.getElementById(domNodeId);
    return container && createPortal(<MarkersWidgetContent />, container);
  }
}
