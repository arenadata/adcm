import type {
  IDisposable,
  CodeEditorModel,
  EditorFile,
  ITextModel,
  ChangeEvent,
  IMarker,
  IStandaloneCodeEditor,
  OpenedFile,
  IEvent,
  MonacoCodeEditorOptions,
  GetSuggestionsCallback,
} from './MonacoCodeEditor.types';
import { monaco, Emitter, languages } from './MonacoCodeEditor.types';
import { createOrUpdateModel } from './MonacoCodeEditor.utils';
import { MonacoCodeEditorOpenedFiles } from './MonacoCodeEditorOpenedFiles';
import type { MonacoYaml } from 'monaco-yaml';
import { configureMonacoYaml } from 'monaco-yaml';

export class MonacoCodeEditorModel implements CodeEditorModel, IDisposable {
  // events
  private onChangeEmitter = new Emitter<ChangeEvent>();
  private onMarkersChangeEmitter = new Emitter<IMarker[]>();
  private onDisposeEmitter = new Emitter<void>();

  // refs
  public readonly editorRef: IStandaloneCodeEditor;
  private monacoYamlRef: MonacoYaml | null = null;

  private currentFile: OpenedFile | null = null;
  private disposables: IDisposable[] = [];
  private autocompletionProvider: IDisposable | null = null;
  private static globalOpenedFiles: MonacoCodeEditorOpenedFiles = new MonacoCodeEditorOpenedFiles();

  constructor(container: HTMLElement) {
    this.editorRef = monaco.editor.create(container);
    this.initEvents();
  }

  get onChange(): IEvent<ChangeEvent> {
    return this.onChangeEmitter.event;
  }

  get onMarkersChange(): IEvent<IMarker[]> {
    return this.onMarkersChangeEmitter.event;
  }

  get onDispose(): IEvent<void> {
    return this.onDisposeEmitter.event;
  }

  public openFile(file: EditorFile): ITextModel {
    this.closeFile();

    const model = createOrUpdateModel(file);
    this.editorRef.setModel(model);
    MonacoCodeEditorModel.globalOpenedFiles.add(file);
    this.setupLanguage(file.language);

    const uri = monaco.Uri.parse(file.uri);
    this.currentFile = { uri, model };
    this.onChangeEmitter.fire({ value: file.text, model });
    return model;
  }

  public closeFile(): void {
    if (this.currentFile) {
      MonacoCodeEditorModel.globalOpenedFiles.remove(this.currentFile.uri);
      this.currentFile.model.dispose();
      this.currentFile = null;
    }
  }

  public setPosition(position: monaco.IPosition): void {
    this.editorRef.setPosition(position);
    this.editorRef.focus();
  }

  public updateOptions(options: MonacoCodeEditorOptions): void {
    this.editorRef.updateOptions({
      glyphMargin: options?.glyphMargin,
      automaticLayout: true,
      theme: options?.theme,
      minimap: { enabled: options?.showMinimap },
      readOnly: options?.isReadOnly,
    });
  }

  public registerAutocomplete(language: string, getSuggestions: GetSuggestionsCallback): void {
    this.autocompletionProvider = languages.registerCompletionItemProvider(language, {
      provideCompletionItems: (model, position) => {
        return {
          suggestions: getSuggestions(model, position),
        };
      },
    });
  }

  public unregisterAutocomplete(): void {
    this.autocompletionProvider?.dispose();
  }

  private initEvents(): void {
    this.disposables.push(
      this.editorRef.onDidChangeModelContent((event) => {
        const model = this.editorRef.getModel();
        if (model) {
          this.onChangeEmitter.fire({ value: this.editorRef.getValue() || '', event, model });
        }
      }),
    );

    this.disposables.push(
      monaco.editor.onDidChangeMarkers(([resource]) => {
        const markers = monaco.editor.getModelMarkers({ resource });
        const currentFileFullUrl = this.currentFile?.uri.toString();
        const modelMarkers = markers.filter((m) => m.resource.toString() === currentFileFullUrl);

        if (modelMarkers.length) {
          this.onMarkersChangeEmitter.fire(modelMarkers);
        }
      }),
    );
  }

  private setupLanguage(language: string, validate = true): void {
    const schemas = MonacoCodeEditorModel.globalOpenedFiles.getSchemas();

    // configure the JSON language support with schemas and schema associations
    if (language === 'json') {
      monaco.languages.json.jsonDefaults.setDiagnosticsOptions({
        schemas,
        validate,
      });
    }

    // configure the Yaml language support with schemas and schema associations
    if (language === 'yaml') {
      const options = {
        enableSchemaRequest: true,
        schemas,
        validate,
      };

      if (this.monacoYamlRef) {
        this.monacoYamlRef.update(options);
      } else {
        this.monacoYamlRef = configureMonacoYaml(monaco, options);
        this.disposables.push(this.monacoYamlRef);
      }
    }
  }

  public dispose(): void {
    this.closeFile();
    this.autocompletionProvider?.dispose();
    this.disposables.forEach((d) => d.dispose());
    this.onDisposeEmitter.fire();
    this.editorRef.dispose();
  }
}
