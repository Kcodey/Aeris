"""
Tests for data-analysis skill.
Validates skill content structure, metric contracts, chart selection logic,
decision brief templates, and analytical pitfalls detection.
"""
import pytest
from pathlib import Path


# Skill directory path
SKILL_DIR = Path(__file__).parent.parent / "skills" / "data-analysis-1.0.2"


class TestSkillStructure:
    """Test that all required skill files exist and have valid structure."""

    def test_skill_directory_exists(self):
        """Skill directory should exist."""
        assert SKILL_DIR.exists(), f"Skill directory not found: {SKILL_DIR}"
        assert SKILL_DIR.is_dir(), f"Expected directory, got file: {SKILL_DIR}"

    def test_skill_md_exists(self):
        """Main SKILL.md file should exist."""
        skill_md = SKILL_DIR / "SKILL.md"
        assert skill_md.exists(), "SKILL.md not found"

    def test_all_reference_files_exist(self):
        """All reference files mentioned in SKILL.md should exist."""
        reference_files = [
            "metric-contracts.md",
            "chart-selection.md",
            "decision-briefs.md",
            "pitfalls.md",
            "techniques.md",
        ]
        for filename in reference_files:
            filepath = SKILL_DIR / filename
            assert filepath.exists(), f"Reference file not found: {filename}"

    def test_skill_md_has_required_sections(self):
        """SKILL.md should have all required sections."""
        skill_md = SKILL_DIR / "SKILL.md"
        content = skill_md.read_text()

        required_sections = [
            "When to Use",
            "Core Principle",
            "Methodology First",
            "Statistical Rigor Checklist",
            "Architecture",
            "Core Rules",
            "Common Traps",
            "Approach Selection",
            "Output Standards",
            "Red Flags to Escalate",
        ]

        for section in required_sections:
            assert section in content, f"Missing required section: {section}"

    def test_skill_md_has_frontmatter(self):
        """SKILL.md should have valid frontmatter with skill metadata."""
        skill_md = SKILL_DIR / "SKILL.md"
        content = skill_md.read_text()

        assert content.startswith("---"), "SKILL.md should start with frontmatter"
        assert 'name: Data Analysis' in content, "Missing skill name in frontmatter"
        assert 'version:' in content, "Missing version in frontmatter"

    def test_approach_selection_has_all_methods(self):
        """Approach selection table should include all expected analysis methods."""
        skill_md = SKILL_DIR / "SKILL.md"
        content = skill_md.read_text()

        expected_methods = [
            "Hypothesis test",
            "Regression",
            "Cohort analysis",
            "Segmentation",
            "Anomaly detection",
        ]

        for method in expected_methods:
            assert method in content, f"Missing expected method: {method}"


class TestMetricContracts:
    """Test metric contracts reference file."""

    def test_metric_contracts_file_exists(self):
        """metric-contracts.md should exist."""
        filepath = SKILL_DIR / "metric-contracts.md"
        assert filepath.exists()

    def test_has_contract_template(self):
        """Should have contract template with all required fields."""
        filepath = SKILL_DIR / "metric-contracts.md"
        content = filepath.read_text()

        required_fields = [
            "Business question",
            "Entity and grain",
            "Numerator and denominator",
            "Filters and exclusions",
            "Time window",
            "Source of truth",
            "Known caveats",
        ]

        for field in required_fields:
            assert field in content, f"Missing metric contract field: {field}"

    def test_has_minimum_contract_output_table(self):
        """Should have minimum contract output table example."""
        filepath = SKILL_DIR / "metric-contracts.md"
        content = filepath.read_text()

        assert "Minimum Contract Output" in content
        assert "Metric" in content
        assert "Paid conversion rate" in content

    def test_has_stop_conditions(self):
        """Should have stop conditions for presenting metrics."""
        filepath = SKILL_DIR / "metric-contracts.md"
        content = filepath.read_text()

        assert "Stop Conditions" in content
        assert "numerator or denominator changed" in content

    def test_has_fast_questions(self):
        """Should have fast questions to ask."""
        filepath = SKILL_DIR / "metric-contracts.md"
        content = filepath.read_text()

        assert "Fast Questions" in content
        assert "What exactly counts in the numerator" in content


class TestChartSelection:
    """Test chart selection reference file."""

    def test_chart_selection_file_exists(self):
        """chart-selection.md should exist."""
        filepath = SKILL_DIR / "chart-selection.md"
        assert filepath.exists()

    def test_has_question_to_chart_map(self):
        """Should have question to chart mapping table."""
        filepath = SKILL_DIR / "chart-selection.md"
        content = filepath.read_text()

        assert "Question to Chart Map" in content
        assert "line chart" in content
        assert "bar chart" in content

    def test_has_default_rules(self):
        """Should have default chart rules."""
        filepath = SKILL_DIR / "chart-selection.md"
        content = filepath.read_text()

        assert "Default Rules" in content
        assert "Bars start at zero" in content

    def test_has_visual_anti_patterns(self):
        """Should document visual anti-patterns."""
        filepath = SKILL_DIR / "chart-selection.md"
        content = filepath.read_text()

        assert "Visual Anti-Patterns" in content
        assert "Pie charts" in content
        assert "Dual-axis" in content

    def test_has_before_shipping_checklist(self):
        """Should have before shipping checklist."""
        filepath = SKILL_DIR / "chart-selection.md"
        content = filepath.read_text()

        assert "Before Shipping" in content or "Check" in content


class TestDecisionBriefs:
    """Test decision briefs reference file."""

    def test_decision_briefs_file_exists(self):
        """decision-briefs.md should exist."""
        filepath = SKILL_DIR / "decision-briefs.md"
        assert filepath.exists()

    def test_has_standard_decision_brief_template(self):
        """Should have standard decision brief template."""
        filepath = SKILL_DIR / "decision-briefs.md"
        content = filepath.read_text()

        assert "Standard Decision Brief" in content
        assert "Decision question" in content
        assert "Evidence" in content
        assert "Confidence" in content
        assert "Recommended next action" in content

    def test_has_experiment_readout(self):
        """Should have experiment readout template."""
        filepath = SKILL_DIR / "decision-briefs.md"
        content = filepath.read_text()

        assert "Experiment Readout" in content
        assert "Hypothesis" in content
        assert "Primary metric" in content
        assert "Ship, iterate, or stop" in content

    def test_has_anomaly_note(self):
        """Should have anomaly note template."""
        filepath = SKILL_DIR / "decision-briefs.md"
        content = filepath.read_text()

        assert "Anomaly Note" in content
        assert "What moved" in content
        assert "Likely drivers" in content

    def test_has_executive_summary(self):
        """Should have executive summary template."""
        filepath = SKILL_DIR / "decision-briefs.md"
        content = filepath.read_text()

        assert "Executive Summary" in content
        assert "One-sentence answer" in content

    def test_has_writing_rules(self):
        """Should have writing rules."""
        filepath = SKILL_DIR / "decision-briefs.md"
        content = filepath.read_text()

        assert "Writing Rules" in content
        assert "Lead with the answer" in content


class TestTechniques:
    """Test techniques reference file."""

    def test_techniques_file_exists(self):
        """techniques.md should exist."""
        filepath = SKILL_DIR / "techniques.md"
        assert filepath.exists()

    def test_has_hypothesis_testing(self):
        """Should have hypothesis testing section."""
        filepath = SKILL_DIR / "techniques.md"
        content = filepath.read_text()

        assert "Hypothesis Testing" in content
        assert "p-value" in content
        assert "Effect size" in content
        assert "Confidence interval" in content

    def test_has_cohort_analysis(self):
        """Should have cohort analysis section."""
        filepath = SKILL_DIR / "techniques.md"
        content = filepath.read_text()

        assert "Cohort Analysis" in content
        assert "Retention cohorts" in content

    def test_has_funnel_analysis(self):
        """Should have funnel analysis section."""
        filepath = SKILL_DIR / "techniques.md"
        content = filepath.read_text()

        assert "Funnel Analysis" in content
        assert "drop-off" in content

    def test_has_regression_analysis(self):
        """Should have regression analysis section."""
        filepath = SKILL_DIR / "techniques.md"
        content = filepath.read_text()

        assert "Regression Analysis" in content
        assert "Linear" in content
        assert "Logistic" in content

    def test_has_segmentation(self):
        """Should have segmentation section."""
        filepath = SKILL_DIR / "techniques.md"
        content = filepath.read_text()

        assert "Segmentation" in content or "Clustering" in content
        assert "K-means" in content

    def test_has_anomaly_detection_section(self):
        """Should have anomaly detection section."""
        filepath = SKILL_DIR / "techniques.md"
        content = filepath.read_text()

        assert "Anomaly Detection" in content
        assert "standard deviations" in content

    def test_has_time_series_analysis(self):
        """Should have time series analysis section."""
        filepath = SKILL_DIR / "techniques.md"
        content = filepath.read_text()

        assert "Time Series" in content
        assert "Trend" in content
        assert "Seasonality" in content


class TestPitfalls:
    """Test analytical pitfalls reference file."""

    def test_pitfalls_file_exists(self):
        """pitfalls.md should exist."""
        filepath = SKILL_DIR / "pitfalls.md"
        assert filepath.exists()

    def test_has_simpsons_paradox(self):
        """Should document Simpson's paradox."""
        filepath = SKILL_DIR / "pitfalls.md"
        content = filepath.read_text()

        assert "Simpson" in content or "Simpson's" in content
        assert "paradox" in content.lower()

    def test_has_survivorship_bias(self):
        """Should document survivorship bias."""
        filepath = SKILL_DIR / "pitfalls.md"
        content = filepath.read_text()

        assert "Survivorship" in content or "survivorship" in content
        assert "bias" in content.lower()

    def test_has_comparing_unequal_periods(self):
        """Should document comparing unequal periods trap."""
        filepath = SKILL_DIR / "pitfalls.md"
        content = filepath.read_text()

        assert "Unequal Periods" in content or "unequal" in content.lower()

    def test_has_p_hacking(self):
        """Should document p-hacking trap."""
        filepath = SKILL_DIR / "pitfalls.md"
        content = filepath.read_text()

        assert "p-Hacking" in content or "p-hacking" in content.lower()
        assert "Multiple Comparisons" in content or "comparisons" in content.lower()

    def test_has_spurious_correlation(self):
        """Should document spurious correlation trap."""
        filepath = SKILL_DIR / "pitfalls.md"
        content = filepath.read_text()

        assert "Spurious" in content
        assert "Correlation" in content

    def test_has_aggregating_percentages(self):
        """Should document aggregating percentages trap."""
        filepath = SKILL_DIR / "pitfalls.md"
        content = filepath.read_text()

        assert "Aggregat" in content
        assert "percentages" in content.lower()

    def test_has_selection_bias(self):
        """Should document selection bias in A/B tests."""
        filepath = SKILL_DIR / "pitfalls.md"
        content = filepath.read_text()

        assert "Selection Bias" in content or "selection bias" in content.lower()

    def test_has_confusing_causation(self):
        """Should document confusing causation trap."""
        filepath = SKILL_DIR / "pitfalls.md"
        content = filepath.read_text()

        assert "Causation" in content or "causation" in content.lower()


class TestStatisticalRigor:
    """Test statistical rigor checklist in SKILL.md."""

    def test_has_statistical_rigor_checklist(self):
        """Should have statistical rigor checklist."""
        skill_md = SKILL_DIR / "SKILL.md"
        content = skill_md.read_text()

        assert "Statistical Rigor Checklist" in content
        assert "Sample size" in content
        assert "Comparison groups" in content
        assert "Effect size" in content

    def test_core_rules_present(self):
        """Should have all 7 core rules."""
        skill_md = SKILL_DIR / "SKILL.md"
        content = skill_md.read_text()

        assert "Core Rules" in content
        assert "Start from the decision" in content
        assert "Lock the metric contract" in content
        assert "Separate extraction" in content
        assert "Choose visuals" in content
        assert "Brief every result" in content
        assert "Stress-test claims" in content
        assert "Escalate when" in content

    def test_red_flags_present(self):
        """Should have red flags to escalate."""
        skill_md = SKILL_DIR / "SKILL.md"
        content = skill_md.read_text()

        assert "Red Flags" in content
        assert "prove" in content.lower()
        assert "Sample size" in content or "small" in content.lower()


class TestSkillMetadata:
    """Test skill metadata and configuration."""

    def test_skill_name_in_frontmatter(self):
        """Skill name should be 'Data Analysis'."""
        skill_md = SKILL_DIR / "SKILL.md"
        content = skill_md.read_text()

        assert 'name: Data Analysis' in content

    def test_skill_version_format(self):
        """Version should follow semver format."""
        skill_md = SKILL_DIR / "SKILL.md"
        content = skill_md.read_text()

        import re
        version_match = re.search(r'version:\s*(\d+\.\d+\.\d+)', content)
        assert version_match, "Version not found in expected format"
        version = version_match.group(1)
        parts = version.split('.')
        assert len(parts) == 3, f"Version should have 3 parts: {version}"

    def test_skill_has_description(self):
        """Skill should have a description."""
        skill_md = SKILL_DIR / "SKILL.md"
        content = skill_md.read_text()

        assert 'description:' in content

    def test_skill_has_when_to_use(self):
        """Skill should clearly state when to use it."""
        skill_md = SKILL_DIR / "SKILL.md"
        content = skill_md.read_text()

        when_to_use_section = content.split("## When to Use")[1].split("##")[0]
        assert len(when_to_use_section) > 100, "When to Use section should be detailed"

    def test_quick_reference_table_present(self):
        """Should have quick reference table mapping topics to files."""
        skill_md = SKILL_DIR / "SKILL.md"
        content = skill_md.read_text()

        assert "Quick Reference" in content
        assert "Metric definition" in content
        assert "Visual selection" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
