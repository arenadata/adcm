import { KNOWN_HTML_TAGS, escapeNonHtmlTags } from '../ErrorAlert.utils';

describe('escapeNonHtmlTags', () => {
  it('should escape non-HTML tags', () => {
    const input = 'Errors: <Host #38 host3>, <Host #39 host3>';
    const result = escapeNonHtmlTags(input);
    expect(result).toBe('Errors: &lt;Host #38 host3&gt;, &lt;Host #39 host3&gt;');
  });

  it('should preserve known HTML tags', () => {
    const input = 'Click <a href="/adcm-web/app/public">here</a> to continue';
    const result = escapeNonHtmlTags(input);
    expect(result).toBe('Click <a href="/adcm-web/app/public">here</a> to continue');
  });

  it('should handle mixed HTML and non-HTML tags', () => {
    const input =
      'Only one copy of a host can be added. Errors: <Host #38 host3>, <Host #39 host3>. <a href="/adcm-web/app/public">Link</a>';
    const result = escapeNonHtmlTags(input);
    expect(result).toBe(
      'Only one copy of a host can be added. Errors: &lt;Host #38 host3&gt;, &lt;Host #39 host3&gt;. <a href="/adcm-web/app/public">Link</a>',
    );
  });

  it('should preserve all known HTML tags', () => {
    KNOWN_HTML_TAGS.forEach((tag) => {
      const input = `<${tag}>content</${tag}>`;
      const result = escapeNonHtmlTags(input);
      expect(result).toBe(input);
    });
  });

  it('should handle tags with attributes', () => {
    const input = '<CustomTag attr="value">content</CustomTag>';
    const result = escapeNonHtmlTags(input);
    expect(result).toBe('&lt;CustomTag attr="value"&gt;content&lt;/CustomTag&gt;');
  });
});
