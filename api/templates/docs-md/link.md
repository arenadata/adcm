{% load rest_framework %}
### <a name="{{ section_key }}-{{ link_key|slugify }}">{{ link.title|default:link_key }}</a> 

__{{ link.action|upper }}__  `{{ link.url }}`


{{ link.description }}

{% if link.fields|with_location:'path' %}
#### Path Parameters
The following parameters should be included in the URL path.

| Parameter | Description |
| --------- | ----------- | {% for field in link.fields|with_location:'path' %}
| `{{ field.name }}`{% if field.required %} __required__{% endif %} | {% if field.schema.description %}{{ field.schema.description }}{% endif %} | {% endfor %}

{% endif %}
{% if link.fields|with_location:'query' %}
    <h4>Query Parameters</h4>
    <p>The following parameters should be included as part of a URL query string.</p>
    <table class="parameters table table-bordered table-striped">
        <thead>
            <tr><th>Parameter</th><th>Description</th></tr>
        </thead>
        <tbody>
            {% for field in link.fields|with_location:'query' %}
            <tr><td class="parameter-name"><code>{{ field.name }}</code>{% if field.required %} <span class="label label-warning">required</span>{% endif %}</td><td>{% if field.schema.description %}{{ field.schema.description }}{% endif %}</td></tr>
            {% endfor %}
        </tbody>
    </table>
{% endif %}
{% if link.fields|with_location:'header' %}
    <h4>Header Parameters</h4>
    <p>The following parameters should be included as HTTP headers.</p>
    <table class="parameters table table-bordered table-striped">
        <thead>
            <tr><th>Parameter</th><th>Description</th></tr>
        </thead>
        <tbody>
            {% for field in link.fields|with_location:'header' %}
            <tr><td class="parameter-name"><code>{{ field.name }}</code>{% if field.required %} <span class="label label-warning">required</span>{% endif %}</td><td>{% if field.schema.description %}{{ field.schema.description }}{% endif %}</td></tr>
            {% endfor %}
        </tbody>
    </table>
{% endif %}
{% if link.fields|with_location:'body' %}
    <h4>Request Body</h4>
    <p>The request body should be <code>"{{ link.encoding }}"</code> encoded, and should contain a single item.</p>
    <table class="parameters table table-bordered table-striped">
        <thead>
            <tr><th>Parameter</th><th>Description</th></tr>
        </thead>
        <tbody>
            {% for field in link.fields|with_location:'body' %}
            <tr><td class="parameter-name"><code>{{ field.name }}</code>{% if field.required %} <span class="label label-warning">required</span>{% endif %}</td><td>{% if field.schema.description %}{{ field.schema.description }}{% endif %}</td></tr>
            {% endfor %}
        </tbody>
    </table>
{% elif link.fields|with_location:'form' %}
#### Request Body
The request body should be a "__{{ link.encoding }}__" encoded object, containing the following items.

| Parameter | Description |
| --------- | ----------- | {% for field in link.fields|with_location:'form' %}
| `{{ field.name }}`{% if field.required %} __required__{% endif %} | {% if field.schema.description %}{{ field.schema.description }}{% endif %} | {% endfor %}
{% endif %}
