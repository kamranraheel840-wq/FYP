"""Shared design tokens for the desktop application."""


class Theme:
    # Application chrome
    NAVY = "#111B2E"
    NAVY_LIGHT = "#1A2940"
    SIDEBAR = "#101827"
    SIDEBAR_HOVER = "#1B2940"
    BLUE = "#2B5EA8"
    BLUE_HOVER = "#234E90"
    BLUE_LIGHT = "#9BBEFF"
    BLUE_SOFT = "#E8F0FF"
    RED = "#B93F4F"
    RED_HOVER = "#963341"
    RED_LIGHT = "#F3A1A9"

    # Workspace surfaces
    BG = "#F3F5F9"
    WHITE = "#FFFFFF"
    CARD = "#FFFFFF"
    CARD_ALT = "#F8FAFD"
    BORDER = "#DCE2EC"
    BORDER_SOFT = "#E8ECF3"
    INPUT = "#FFFFFF"

    # Text
    TEXT = "#172338"
    TEXT_MUTED = "#5B687B"
    TEXT_WHITE = "#FFFFFF"
    TEXT_SOFT = "#AAB6C8"
    TEXT_ON_DARK = "#E8EDF5"

    # Semantic colors
    SUCCESS = "#176F57"
    SUCCESS_SOFT = "#E4F4EE"
    WARNING = "#875417"
    WARNING_SOFT = "#FFF2DE"
    GOLD = "#D8AE63"
    INFO = "#4E8CF7"

    FONT = "Segoe UI"
    FONT_DISPLAY = "Segoe UI"
    F_TITLE = (FONT_DISPLAY, 21, "bold")
    F_HEADING = (FONT, 15, "bold")
    F_SUBHEAD = (FONT, 11, "bold")
    F_BODY = (FONT, 10)
    F_SMALL = (FONT, 9)
    F_BUTTON = (FONT, 10, "bold")
    F_TAB = (FONT, 10, "bold")
    F_LOGO = (FONT_DISPLAY, 16, "bold")
    F_STAT = (FONT_DISPLAY, 25, "bold")

    ROW_ALT = "#F7F9FC"
    STATUS = {
        "Wanted": ("#FCE9EC", "#A63142"),
        "Arrested": ("#FFF0E3", "#985B22"),
        "Incarcerated": ("#E8F0FF", "#315FA9"),
        "Released": ("#E5F4EC", "#25704F"),
        "Deceased": ("#E9EDF2", "#536174"),
    }
