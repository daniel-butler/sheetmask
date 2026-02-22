from sheetmask import PercentageVarianceRule, PreserveRelationshipRule

config = {
    "version": "1.0.0",
    "sheets_to_keep": ["Summary", "Details", "Team"],
    "entity_columns": {
        # Summary sheet
        "Client": "ORGANIZATION",
        "Account Manager": "PERSON",
        # Details sheet
        "Project Name": "PROJECT_NAME",
        "Project Manager": "PERSON",
        "Description": "PROJECT_DESCRIPTION",
        # Team sheet
        "Name": "PERSON",
        "Email": "EMAIL_ADDRESS",
        "Phone": "PHONE_NUMBER",
        "Office": "LOCATION",
    },
    "numeric_rules": {
        "Revenue": PercentageVarianceRule(variance_pct=0.2),
        "Cost": PercentageVarianceRule(variance_pct=0.2),
        "Gross Margin": PreserveRelationshipRule(
            formula="context['Revenue'] - context['Cost']",
            dependent_columns=["Revenue", "Cost"],
        ),
        "GM%": PreserveRelationshipRule(
            formula="(context['Gross Margin'] / context['Revenue'] * 100).round(2)",
            dependent_columns=["Gross Margin", "Revenue"],
        ),
        "Billed": PercentageVarianceRule(variance_pct=0.2),
        "Expenses": PercentageVarianceRule(variance_pct=0.2),
        "Net": PreserveRelationshipRule(
            formula="context['Billed'] - context['Expenses']",
            dependent_columns=["Billed", "Expenses"],
        ),
    },
    "preserve_columns": ["Start Date", "End Date", "Title", "Office"],
}
