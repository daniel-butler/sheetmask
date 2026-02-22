from sheetmask import PercentageVarianceRule, PreserveRelationshipRule

config = {
    "version": "1.0.0",
    "sheets_to_keep": ["Roster"],
    "entity_columns": {
        "First Name": "PERSON_FIRST_NAME",
        "Last Name": "PERSON_LAST_NAME",
        "Full Name": "PERSON",
        "Email": "EMAIL_ADDRESS",
        "Phone": "PHONE_NUMBER",
        "Location": "LOCATION",
    },
    "numeric_rules": {
        "Base Salary": PercentageVarianceRule(variance_pct=0.15),
        "Annual Bonus": PreserveRelationshipRule(
            formula="(context['Base Salary'] * context['Bonus %'] / 100).round(0)",
            dependent_columns=["Base Salary", "Bonus %"],
        ),
    },
    "preserve_columns": ["Employee ID", "Department", "Title", "Hire Date", "Bonus %"],
}
