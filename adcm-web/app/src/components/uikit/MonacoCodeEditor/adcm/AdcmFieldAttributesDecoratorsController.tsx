import type { ConfigurationAttributes, FieldAttributes } from '@models/adcm';
import { monaco } from '../MonacoCodeEditor.types';
import type {
  IModelDeltaDecoration,
  IStandaloneCodeEditor,
  SymbolsDictionary,
  IMouseTarget,
  IPosition,
  IEditorDecorationsCollection,
  ITextModel,
  IDisposable,
  IEditorMouseEvent,
} from '../MonacoCodeEditor.types';
import s from './AdcmFieldAttributesDecorator.module.scss';
import type { InjectedText } from 'monaco-editor/esm/vs/editor/common/modelLineProjectionData.js';
import type { NodesDictionary } from './AdcmConfigEditor.types';

type DecoratorAttachedData = {
  key: 'adcm-field-attribute';
  path: string;
  attribute: FieldAttributes;
  position: IPosition;
};

export type AdcmFieldAttributesDecoratorClickEventDetails = {
  model: ITextModel;
  path: string;
  attributes: FieldAttributes;
  position: IPosition;
};

export class AdcmFieldAttributesDecoratorsController extends EventTarget {
  private disposables: IDisposable[] = [];
  private decorationsCollection: IEditorDecorationsCollection | null = null;
  private editor: IStandaloneCodeEditor;

  // src/vs/editor/contrib/colorPicker/browser/hoverColorPicker/hoverColorPickerParticipant.ts

  constructor(editor: IStandaloneCodeEditor) {
    super();
    this.editor = editor;
    this.init();
  }

  public decorate(
    attributes: ConfigurationAttributes,
    symbolsDictionary: SymbolsDictionary,
    nodesDictionary: NodesDictionary,
  ) {
    const newDecorators = this.getDecorators(attributes, symbolsDictionary, nodesDictionary);
    this.decorationsCollection?.clear();
    this.decorationsCollection = this.editor?.createDecorationsCollection(newDecorators);
  }

  private getDecoratorMouseEventAttachedData(target: IMouseTarget | null) {
    if (!target) {
      return null;
    }

    if (target.type !== monaco.editor.MouseTargetType.CONTENT_TEXT) {
      return null;
    }

    // biome-ignore lint/suspicious/noExplicitAny:
    const injectedText = (target.detail as any).injectedText as InjectedText;

    if (!injectedText) {
      return null;
    }

    if (injectedText.options.attachedData?.key === 'adcm-field-attribute') {
      return injectedText.options.attachedData as DecoratorAttachedData;
    }

    return null;
  }

  private handleClickDecorator(mouseEvent: IEditorMouseEvent, editor: IStandaloneCodeEditor) {
    const model = editor.getModel();
    const decoratorMouseEvent = this.getDecoratorMouseEventAttachedData(mouseEvent.target);
    if (model && decoratorMouseEvent) {
      const detail: AdcmFieldAttributesDecoratorClickEventDetails = {
        model,
        path: decoratorMouseEvent.path,
        attributes: decoratorMouseEvent.attribute,
        position: decoratorMouseEvent.position,
      };
      this.dispatchEvent(new CustomEvent('click', { detail }));
    }
  }

  public init() {
    const clickHandler = this.editor.onMouseDown((event) => this.handleClickDecorator(event, this.editor));
    this.disposables.push(clickHandler);
  }

  public dispose() {
    for (const d of this.disposables) {
      d.dispose();
    }
  }

  public getDecorators(
    attributes: ConfigurationAttributes,
    symbolsDictionary: SymbolsDictionary,
    nodesDictionary: NodesDictionary,
  ) {
    const paths = Object.keys(attributes);

    const decorators: IModelDeltaDecoration[] = [];

    for (const path of paths) {
      const symbol = symbolsDictionary[path];

      if (symbol === undefined) {
        continue;
      }

      const attribute = attributes[path];

      let content = '\xa0';
      content += attribute.isActive ? '✅' : '⬜';
      content += attribute.isSynchronized ? '🔗' : '⛓️‍💥';

      // add icons
      const attachedData: DecoratorAttachedData = {
        key: 'adcm-field-attribute',
        path,
        attribute,
        position: {
          column: symbol.selectionRange.endColumn,
          lineNumber: symbol.selectionRange.endLineNumber,
        },
      };

      decorators.push({
        range: {
          startColumn: symbol.selectionRange.startColumn,
          startLineNumber: symbol.selectionRange.startLineNumber,
          endColumn: symbol.selectionRange.endColumn,
          endLineNumber: symbol.selectionRange.endLineNumber,
        },
        options: {
          after: {
            content,
            attachedData,
            inlineClassNameAffectsLetterSpacing: true,
            inlineClassName: s.adcmFieldAttributesDecorator,
          },
        },
      });

      // set text color for inactive group
      if (!attribute.isActive) {
        decorators.push({
          range: {
            startColumn: symbol.range.startColumn,
            startLineNumber: symbol.range.startLineNumber,
            endColumn: symbol.range.endColumn,
            endLineNumber: symbol.range.endLineNumber,
          },
          options: {
            inlineClassName: s.adcmDeactivatedField,
          },
        });

        // add line decorator
        decorators.push({
          range: {
            startColumn: symbol.range.startColumn,
            startLineNumber: symbol.range.startLineNumber,
            endColumn: symbol.range.endColumn,
            endLineNumber: symbol.range.endLineNumber,
          },
          options: {
            isWholeLine: true,
            linesDecorationsClassName: s.adcmDeactivatedFieldLineDecoration,
          },
        });
      }
    }

    const nodesPaths = Object.keys(nodesDictionary);

    for (const path of nodesPaths) {
      const node = nodesDictionary[path];
      if (node.data.fieldSchema.adcmMeta.isAdvanced) {
        const symbol = symbolsDictionary[path];
        if (symbol) {
          //  text color decorator
          decorators.push({
            range: {
              startColumn: symbol.range.startColumn,
              startLineNumber: symbol.range.startLineNumber,
              endColumn: symbol.range.endColumn,
              endLineNumber: symbol.range.endLineNumber,
            },
            options: {
              inlineClassName: s.adcmAdvancedField,
            },
          });
          // line decorator
          decorators.push({
            range: {
              startColumn: symbol.range.startColumn,
              startLineNumber: symbol.range.startLineNumber,
              endColumn: symbol.range.endColumn,
              endLineNumber: symbol.range.endLineNumber,
            },
            options: {
              isWholeLine: true,
              linesDecorationsClassName: s.adcmAdvancedFieldLineDecoration,
            },
          });
        }
      }

      if (node.data.fieldSchema.adcmMeta.isInvisible) {
        const symbol = symbolsDictionary[path];
        if (symbol) {
          //  text color decorator
          decorators.push({
            range: {
              startColumn: symbol.range.startColumn,
              startLineNumber: symbol.range.startLineNumber,
              endColumn: symbol.range.endColumn,
              endLineNumber: symbol.range.endLineNumber,
            },
            options: {
              inlineClassName: s.adcmInvisibleField,
            },
          });

          // line decorator
          decorators.push({
            range: {
              startColumn: symbol.range.startColumn,
              startLineNumber: symbol.range.startLineNumber,
              endColumn: symbol.range.endColumn,
              endLineNumber: symbol.range.endLineNumber,
            },
            options: {
              isWholeLine: true,
              linesDecorationsClassName: s.adcmInvisibleFieldLineDecoration,
            },
          });
        }
      }
    }

    return decorators;
  }
}
