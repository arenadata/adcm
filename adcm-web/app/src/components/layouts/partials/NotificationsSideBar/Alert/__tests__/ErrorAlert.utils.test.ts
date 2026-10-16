import { KNOWN_HTML_TAGS, escapeNonHtmlTags, sanitizeErrorAlertHtml } from '../ErrorAlert.utils';

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

describe('sanitizeErrorAlertHtml', () => {
  it('should escape host-like tags and keep safe links', () => {
    const input = 'Errors: <Host #38 host3>. <a href="/adcm-web/app/public">Link</a>';
    const result = sanitizeErrorAlertHtml(input);

    expect(result).toContain('&lt;Host #38 host3&gt;');
    expect(result).toContain('<a href="/adcm-web/app/public">Link</a>');
  });

  it('should strip event handler attributes from whitelisted tags', () => {
    const result = sanitizeErrorAlertHtml('<span onclick="alert(1)">click</span>');

    expect(result).toBe('<span>click</span>');
    expect(result).not.toContain('onclick');
  });

  it('should remove javascript: href values', () => {
    const result = sanitizeErrorAlertHtml('<a href="javascript:alert(1)">link</a>');

    expect(result).not.toMatch(/javascript:/i);
    expect(result).toContain('link');
  });

  it('should remove data: href values', () => {
    const result = sanitizeErrorAlertHtml('<a href="data:text/html,<script>alert(1)</script>">link</a>');

    expect(result).not.toMatch(/data:/i);
    expect(result).toContain('link');
  });

  it('should neutralize non-whitelisted tags like img with onerror as text', () => {
    const result = sanitizeErrorAlertHtml('<img src=x onerror=alert(1)>safe');

    expect(result).not.toContain('<img');
    expect(result).toBe('&lt;img src=x onerror=alert(1)&gt;safe');
  });

  it('should keep allowed formatting tags', () => {
    const result = sanitizeErrorAlertHtml('<strong>bold</strong> and <em>italic</em>');

    expect(result).toBe('<strong>bold</strong> and <em>italic</em>');
  });
});
