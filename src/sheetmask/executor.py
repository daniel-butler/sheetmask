"""
Anonymization executor for processing Excel files with processor configs.

Architecture:
    1. Load anonymization_config
    2. Load Excel file sheets
    3. Filter sheets (keep only configured sheets)
    4. Anonymize entities (global consistency via EntityMapper)
    5. Anonymize numerics (apply rules with context)
    6. Preserve configured columns
    7. Write anonymized Excel file
"""
import json
import random as stdlib_random
import pandas as pd
from pathlib import Path
from typing import Dict

from sheetmask.entity_mapper import EntityMapper
from sheetmask.rules import NumericAnonymizationRule, PercentageVarianceRule, PreserveRelationshipRule


class AnonymizationExecutor:
    """
    Execute anonymization on Excel files using configs.

    Example:
        config = {
            "sheets_to_keep": ["Sheet1"],
            "entity_columns": {"Name": "PERSON"},
            "numeric_rules": {"Revenue": PercentageVarianceRule(variance_pct=0.3)},
            "preserve_columns": ["Date"],
        }
        executor = AnonymizationExecutor(config, seed=42)

        executor.anonymize_file(
            input_path="Dec-24 Report.xlsx",
            output_path="Dec-24 Report (anonymized).xlsx"
        )
    """

    def __init__(self, config: dict, seed: int | None = None):
        """
        Initialize executor with anonymization config.

        Args:
            config: Anonymization config dict
            seed: Random seed for reproducible anonymization
        """
        self.config = config
        self.entity_mapper = EntityMapper(seed=seed)
        self.seed = seed
        self.rng = stdlib_random.Random(seed) if seed is not None else stdlib_random.Random()

    def anonymize_file(self, input_path: str | Path, output_path: str | Path, auto_suffix: bool = True) -> dict:
        """
        Anonymize Excel file and write to output path.

        Args:
            input_path: Path to original Excel file
            output_path: Path to write anonymized file
            auto_suffix: If True, automatically add "(ANONYMIZED)" suffix if not present

        Returns:
            Dict with anonymization stats (sheets processed, entities mapped, etc.)
        """
        input_path = Path(input_path)
        output_path = Path(output_path)

        # Ensure output filename indicates it's anonymized (unless disabled)
        if auto_suffix and "(ANONYMIZED)" not in output_path.stem:
            # Insert "(ANONYMIZED)" before file extension
            output_path = output_path.with_stem(f"{output_path.stem} (ANONYMIZED)")

        # Step 1: Load all sheets
        print(f"Loading: {input_path.name}")
        xls = pd.ExcelFile(input_path)
        all_sheets = {name: pd.read_excel(input_path, sheet_name=name) for name in xls.sheet_names}
        print(f"  Loaded {len(all_sheets)} sheets")

        # Step 2: Filter sheets (keep only configured sheets)
        sheets_to_keep = self.config.get("sheets_to_keep")
        if sheets_to_keep:
            filtered_sheets = {name: df for name, df in all_sheets.items() if name in sheets_to_keep}
            print(f"  Keeping {len(filtered_sheets)}/{len(all_sheets)} sheets: {list(filtered_sheets.keys())}")
            if not filtered_sheets:
                available = list(all_sheets.keys())
                missing = [s for s in sheets_to_keep if s not in all_sheets]
                raise ValueError(
                    f"No sheets found after filtering. "
                    f"Requested: {sheets_to_keep}. "
                    f"Available sheets: {available}. "
                    f"Missing: {missing}"
                )
        else:
            filtered_sheets = all_sheets
            print(f"  No sheet filtering (keeping all {len(filtered_sheets)} sheets)")

        # Step 3: Anonymize each sheet
        anonymized_sheets = {}
        for sheet_name, df in filtered_sheets.items():
            print(f"\nProcessing '{sheet_name}' ({len(df)} rows x {len(df.columns)} cols)")
            anonymized_df = self._anonymize_sheet(df, sheet_name)
            anonymized_sheets[sheet_name] = anonymized_df
            print("  Done")

        # Step 4: Write to Excel
        print(f"\nWriting: {output_path.name}")
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            for sheet_name, df in anonymized_sheets.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"  Wrote '{sheet_name}'")

        # Step 5: Return stats
        stats = {
            "input_file": str(input_path),
            "output_file": str(output_path),
            "sheets_processed": len(anonymized_sheets),
            "total_rows": sum(len(df) for df in anonymized_sheets.values()),
            "entity_mappings": self.entity_mapper.to_dict(),
        }

        print("\nAnonymization complete!")
        print(f"  Input: {input_path}")
        print(f"  Output: {output_path}")
        print(f"  Sheets: {len(anonymized_sheets)}")
        print(f"  Total entities anonymized: {stats['entity_mappings']['total_mappings']}")

        return stats

    def _anonymize_sheet(self, df: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
        """
        Anonymize a single sheet.

        Args:
            df: DataFrame to anonymize
            sheet_name: Sheet name (for logging)

        Returns:
            Anonymized DataFrame
        """
        df = df.copy()

        # Step 1: Anonymize entity columns
        entity_columns = self.config.get("entity_columns", {})
        for col_name, entity_type in entity_columns.items():
            if col_name in df.columns:
                print(f"    Anonymizing entities: {col_name} ({entity_type})")
                df[col_name] = df[col_name].apply(
                    lambda val: self._anonymize_entity(val, entity_type)
                )

        # Step 2: Anonymize numeric columns
        numeric_rules = self.config.get("numeric_rules", {})
        if numeric_rules:
            df = self._apply_numeric_rules(df, numeric_rules)

        # Step 3: Preserve columns (already preserved by only modifying entity/numeric cols)

        return df

    def _anonymize_entity(self, value, entity_type: str) -> str:
        """
        Anonymize a single entity value.

        Args:
            value: Original value
            entity_type: Entity type (PERSON, ORGANIZATION, etc.)

        Returns:
            Anonymized value (or original if null/empty)
        """
        # Skip null/empty values
        if pd.isna(value) or value == "":
            return value

        # Convert to string for mapping
        original_str = str(value)

        # Get or create fake value (globally consistent)
        fake_value = self.entity_mapper.get_or_create(entity_type, original_str)

        return fake_value

    def _apply_numeric_rules(
        self, df: pd.DataFrame, numeric_rules: Dict[str, NumericAnonymizationRule]
    ) -> pd.DataFrame:
        """
        Apply numeric anonymization rules to DataFrame.

        Args:
            df: DataFrame to anonymize
            numeric_rules: Dict of column_name -> NumericAnonymizationRule

        Returns:
            DataFrame with anonymized numeric columns
        """
        df = df.copy()

        # Build context dict (all columns available for relationship rules)
        context = {col: df[col] for col in df.columns}

        # Apply rules in dependency order
        # First: Apply PercentageVarianceRule (base values)
        # Second: Apply PreserveRelationshipRule (derived values)

        # Phase 1: Base values (PercentageVarianceRule)
        for col_name, rule in numeric_rules.items():
            if col_name not in df.columns:
                continue

            if isinstance(rule, PercentageVarianceRule):
                # Inject executor's seeded rng for reproducibility
                rule_with_rng = PercentageVarianceRule(
                    variance_pct=rule.variance_pct,
                    rng=self.rng,
                )
                print(f"    Anonymizing numeric: {col_name} (±{rule.variance_pct*100:.0f}% variance)")
                df[col_name] = rule_with_rng.apply(df[col_name], context)
                # Update context with anonymized value
                context[col_name] = df[col_name]

        # Phase 2: Derived values (PreserveRelationshipRule)
        for col_name, rule in numeric_rules.items():
            if col_name not in df.columns:
                continue

            if isinstance(rule, PreserveRelationshipRule):
                print(f"    Recomputing: {col_name} (from {', '.join(rule.dependent_columns)})")
                df[col_name] = rule.apply(df[col_name], context)
                # Update context with recomputed value
                context[col_name] = df[col_name]

        return df

    def export_mapping_report(self, output_path: str | Path):
        """
        Export entity mapping report for audit trail.

        Args:
            output_path: Path to write mapping report (JSON)
        """

        output_path = Path(output_path)
        mappings = self.entity_mapper.to_dict()

        with open(output_path, "w") as f:
            json.dump(mappings, f, indent=2)

        print(f"Mapping report exported: {output_path}")
