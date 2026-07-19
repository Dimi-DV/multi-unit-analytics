{#- Use custom schema names exactly as written (staging, marts) instead of
    dbt's default target-prefixed names, so the schemas match what the loader
    and the analysis queries already use. -#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
