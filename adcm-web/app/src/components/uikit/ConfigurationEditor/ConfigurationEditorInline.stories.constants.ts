import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const inlineEditConfigurationSchema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  type: 'object',
  title: 'Configuration',
  readOnly: false,
  properties: {
    repo_settings: {
      type: 'object',
      title: 'Repository settings',
      additionalProperties: false,
      readOnly: false,
      properties: {
        monitoring_repo_mode: {
          type: 'string',
          title: 'Set up monitoring repo',
          description: 'Choose how monitoring repository is configured',
          enum: ['static', 'dynamic'],
          default: 'dynamic',
          readOnly: false,
          adcmMeta: {
            enumExtra: {
              labels: ['Static', 'Dynamic'],
            },
          },
        },
        monitoring_repo_url: {
          type: 'string',
          title: 'Monitoring repo url',
          description: 'URL of the monitoring repository',
          default: 'https://repo.example.com/monitoring',
          readOnly: false,
        },
        monitoring_repo_url_long: {
          type: 'string',
          title: 'Monitoring repo url long',
          description: 'Long inline string for ellipsis and hover buttons width test',
          default:
            'https://repo.example.com/monitoring/very/long/path/that/should/be/truncated/with/ellipsis/when/space/is/limited',
          readOnly: false,
        },
        use_existing_docker: {
          type: 'boolean',
          title: 'Use existing docker',
          description: 'Reuse an existing docker installation',
          default: false,
          readOnly: false,
        },
      },
      required: ['monitoring_repo_mode', 'monitoring_repo_url', 'monitoring_repo_url_long', 'use_existing_docker'],
    },
    network_settings: {
      type: 'object',
      title: 'Network settings',
      additionalProperties: false,
      readOnly: false,
      properties: {
        port: {
          type: 'integer',
          title: 'Port',
          description: 'Service port number',
          default: 8080,
          minimum: 1,
          maximum: 65535,
          readOnly: false,
        },
        timeout: {
          type: 'number',
          title: 'Timeout',
          description: 'Connection timeout in seconds',
          default: 30,
          minimum: 0,
          maximum: 300,
          readOnly: false,
        },
        ratio: {
          type: 'number',
          title: 'Float ratio',
          description: 'Fraction between 0 and 1',
          default: 0.75,
          minimum: 0,
          maximum: 1,
          readOnly: false,
        },
        pi_approx: {
          type: 'number',
          title: 'Pi approximation',
          description: 'Float number field',
          default: Math.PI,
          readOnly: false,
        },
        host: {
          type: 'string',
          title: 'Host',
          default: 'localhost',
          readOnly: false,
          adcmMeta: {
            stringExtra: {
              suggestions: ['localhost', 'host1', 'host2'],
            },
          },
        },
        protocol: {
          type: 'string',
          title: 'Protocol',
          enum: ['http', 'https'],
          default: 'https',
          readOnly: false,
          adcmMeta: {
            enumExtra: {
              labels: ['HTTP', 'HTTPS'],
            },
          },
        },
        environment: {
          type: 'string',
          title: 'Environment',
          description: 'Select width test: empty value should match "Select" placeholder, not longest option',
          enum: ['dev', 'staging', 'production'],
          readOnly: false,
          adcmMeta: {
            enumExtra: {
              labels: [
                'Dev',
                'Staging environment with a very long label name',
                'Production environment with an even longer label for width testing',
              ],
            },
          },
        },
      },
      required: ['port', 'timeout', 'ratio', 'pi_approx', 'host', 'protocol'],
    },
    advanced_settings: {
      type: 'object',
      title: 'Advanced settings',
      additionalProperties: false,
      readOnly: false,
      properties: {
        secret_token: {
          type: 'string',
          title: 'Secret token',
          description: 'Opens in modal (not inline)',
          default: 'secret-value',
          readOnly: false,
          adcmMeta: {
            isSecret: true,
          },
        },
        multiline_config: {
          type: 'string',
          title: 'Multiline config',
          description: 'Opens in modal (not inline)',
          default: 'key: value',
          readOnly: false,
          adcmMeta: {
            stringExtra: {
              isMultiline: true,
            },
          },
        },
        readonly_field: {
          type: 'string',
          title: 'Readonly field',
          default: 'read only value',
          readOnly: true,
        },
      },
    },
  },
  required: ['repo_settings', 'network_settings'],
};

export const inlineEditConfigurationData: ConfigurationData = {
  repo_settings: {
    monitoring_repo_mode: 'dynamic',
    monitoring_repo_url: 'https://repo.example.com/monitoring',
    monitoring_repo_url_long:
      'https://repo.example.com/monitoring/very/long/path/that/should/be/truncated/with/ellipsis/when/space/is/limited',
    use_existing_docker: false,
  },
  network_settings: {
    port: 8080,
    timeout: 30,
    ratio: 0.75,
    pi_approx: Math.PI,
    host: 'localhost',
    protocol: 'https',
    environment: null,
  },
  advanced_settings: {
    secret_token: 'secret-value',
    multiline_config: 'key: value',
    readonly_field: 'read only value',
  },
};
