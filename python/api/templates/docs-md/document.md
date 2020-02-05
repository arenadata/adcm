{% load rest_framework %}


# {{ document.title }}
    {% if document.description %}
    {{ document.description }}
    {% endif %}

## API Sections
{% for section_key, section in document|data|items %}
[{{ section_key }}](#{{ section_key }})
{% endfor %}

{% if document|data %}
{% for section_key, section in document|data|items %}
{% if section_key %}
## {{ section_key }}
{% endif %}
    {% for link_key, link in section|schema_links|items %}
        {% include "docs-md/link.md" %}
    {% endfor %}
{% endfor %}

{% for link_key, link in document.links|items %}
    {% include "docs-md/link.md" %}
{% endfor %}
{% endif %}
