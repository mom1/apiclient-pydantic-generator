{{#versions}}
#### Release notes for `{{#tag}}{{{tag}}}{{/tag}}{{^tag}}{{{label}}}{{/tag}}` ({{{date}}})

{{#sections}}
##### {{{label}}}

{{#commits}}
- {{{subject}}}
{{#body}}
{{{body_indented}}}
{{/body}}
{{/commits}}

{{/sections}}

{{/versions}}
