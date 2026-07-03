from ui.design_system import DashboardDesignSystem
from ui.theme import Theme


def test_design_system_exposes_dashboard_tokens():
    assert DashboardDesignSystem.Colors.BACKGROUND.startswith("#")
    assert DashboardDesignSystem.Typography.TITLE_PT > DashboardDesignSystem.Typography.BASE_PT
    assert DashboardDesignSystem.Spacing.LG > DashboardDesignSystem.Spacing.SM
    assert DashboardDesignSystem.Radius.LG >= DashboardDesignSystem.Radius.MD


def test_theme_uses_design_system_tokens():
    assert Theme.BACKGROUND == DashboardDesignSystem.Colors.BACKGROUND
    assert Theme.CARD_BACKGROUND == DashboardDesignSystem.Colors.CARD
    assert Theme.BORDER == DashboardDesignSystem.Colors.BORDER
    assert Theme.ACCENT == DashboardDesignSystem.Colors.ACCENT


def test_design_system_style_helpers_are_reusable():
    card_style = DashboardDesignSystem.card_style()
    table_style = DashboardDesignSystem.table_style()
    section_style = DashboardDesignSystem.section_title_style()

    assert "background-color" in card_style
    assert "border-radius" in card_style
    assert "alternate-background-color" in table_style
    assert "font-weight" in section_style
