class ReportTemplate {
  final String id;
  final String name;
  final String description;
  final String type;
  final List<ReportParameter> parameters;

  const ReportTemplate({
    required this.id,
    required this.name,
    required this.description,
    required this.type,
    required this.parameters,
  });

  factory ReportTemplate.fromJson(Map<String, dynamic> json) =>
      ReportTemplate(
        id: json['id'] as String,
        name: json['name'] as String,
        description: json['description'] as String,
        type: json['type'] as String,
        parameters: (json['parameters'] as List?)
                ?.map((e) => ReportParameter.fromJson(e))
                .toList() ??
            [],
      );
}

class ReportParameter {
  final String name;
  final String type;
  final String label;
  final bool required;
  final dynamic defaultValue;

  const ReportParameter({
    required this.name,
    required this.type,
    required this.label,
    required this.required,
    this.defaultValue,
  });

  factory ReportParameter.fromJson(Map<String, dynamic> json) =>
      ReportParameter(
        name: json['name'] as String,
        type: json['type'] as String,
        label: json['label'] as String,
        required: json['required'] as bool? ?? false,
        defaultValue: json['default_value'],
      );
}

class RenderedReport {
  final String templateId;
  final String content;
  final String format;
  final DateTime renderedAt;

  const RenderedReport({
    required this.templateId,
    required this.content,
    required this.format,
    required this.renderedAt,
  });

  factory RenderedReport.fromJson(Map<String, dynamic> json) =>
      RenderedReport(
        templateId: json['template_id'] as String,
        content: json['content'] as String,
        format: json['format'] as String,
        renderedAt: DateTime.parse(json['rendered_at'] as String),
      );
}
