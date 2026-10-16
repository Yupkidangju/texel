from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    key: str
    menu: str
    shortcut: str = ""


COMMANDS = [
    Command(key, menu, shortcut)
    for menu, items in {
        "file": [
            ("new", "Ctrl+N"),
            ("open", "Ctrl+O"),
            ("save", "Ctrl+S"),
            ("export", "Ctrl+Shift+S"),
            ("backup", ""),
            ("demo", ""),
            ("quit", "Ctrl+Q"),
        ],
        "edit": [
            ("undo", "Ctrl+Z"),
            ("redo", "Ctrl+Y"),
            ("copy", "Ctrl+C"),
            ("cut", "Ctrl+X"),
            ("paste", "Ctrl+V"),
            ("transpose", ""),
            ("paste_special", ""),
            ("clear", "Delete"),
            ("clear_all", ""),
            ("clear_formats", ""),
            ("select_all", "Ctrl+A"),
            ("select_row", "Shift+Space"),
            ("select_column", "Ctrl+Space"),
            ("fill_down", "Ctrl+D"),
            ("fill_right", "Ctrl+R"),
            ("series", ""),
            ("find", "Ctrl+F"),
            ("replace", "Ctrl+H"),
        ],
        "view": [
            ("goto", "Ctrl+G"),
            ("freeze", ""),
            ("unfreeze", ""),
            ("hide_rows", ""),
            ("hide_columns", ""),
            ("unhide", ""),
            ("width", ""),
            ("autofit", ""),
            ("row_height", ""),
            ("autofit_rows", ""),
            ("formulas", "Ctrl+`"),
            ("theme", "F6"),
            ("language", ""),
        ],
        "insert": [
            ("add_sheet", ""),
            ("rename_sheet", ""),
            ("duplicate_sheet", ""),
            ("delete_sheet", ""),
            ("insert_rows", ""),
            ("delete_rows", ""),
            ("insert_columns", ""),
            ("delete_columns", ""),
            ("named_range", ""),
            ("names", ""),
        ],
        "format": [
            ("style", ""),
            ("borders", ""),
            ("bold", "Ctrl+B"),
            ("italic", "Ctrl+I"),
            ("strike", ""),
            ("wrap", ""),
            ("underline", ""),
            ("note", ""),
            ("merge", ""),
            ("merge_center", ""),
            ("unmerge", ""),
            ("validation", ""),
            ("clear_validation", ""),
            ("conditional", ""),
            ("clear_conditional", ""),
            ("lock", ""),
            ("protect", ""),
        ],
        "data": [
            ("sort", ""),
            ("advanced_sort", ""),
            ("filter", ""),
            ("advanced_filter", ""),
            ("clear_filter", ""),
            ("deduplicate", ""),
        ],
        "analysis": [("profile", ""), ("pivot", ""), ("chart", "")],
        "help": [
            ("help", "F1"),
            ("functions", ""),
            ("history", ""),
            ("inspect", ""),
            ("trace_formula", ""),
            ("mcp_info", ""),
        ],
    }.items()
    for key, shortcut in items
]
