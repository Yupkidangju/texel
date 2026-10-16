"""고급 표 정리와 수식 진단의 공개 UI 동작."""

from ..addresses import MAX_COLUMNS, MAX_ROWS, CellRange, address
from ..diagnostics import trace_dependencies
from ..tables import find_next_match, replace_matches, set_filter, sort_table
from .dialogs import Field

ADVANCED_COMMANDS = {
    "advanced_sort",
    "advanced_filter",
    "find",
    "replace",
    "trace_formula",
    "select_all",
    "select_row",
    "select_column",
}


class AdvancedActionsMixin:
    def advanced_command(self, command):
        sheet, region = self.sheet_index, self.data_region()
        if command == "advanced_sort":
            fields = [Field("range", region)]
            for i in range(1, 4):
                fields.extend(
                    [
                        Field(f"sort_column_{i}", "1" if i == 1 else ""),
                        Field(f"descending_{i}", False),
                    ]
                )
            fields.append(Field("header", True))

            def sort(values):
                keys = [
                    {
                        "column": int(values[f"sort_column_{i}"]) - 1,
                        "descending": values[f"descending_{i}"],
                    }
                    for i in range(1, 4)
                    if values[f"sort_column_{i}"].strip()
                ]
                self.mutate(
                    command, lambda w: sort_table(w, sheet, values["range"], keys, values["header"])
                )

            self.form(command, fields, sort)
        elif command == "advanced_filter":
            fields = [Field("range", region), Field("filter_match", "all", ["all", "any"])]
            for i in range(1, 4):
                fields.extend(
                    [Field(f"filter_column_{i}", "1" if i == 1 else ""), Field(f"criterion_{i}")]
                )
            fields.append(Field("header", True))

            def filter_data(values):
                conditions = [
                    {
                        "column": int(values[f"filter_column_{i}"]) - 1,
                        "criterion": values[f"criterion_{i}"],
                    }
                    for i in range(1, 4)
                    if values[f"filter_column_{i}"].strip()
                ]
                self.mutate(
                    command,
                    lambda w: set_filter(
                        w,
                        sheet,
                        values["range"],
                        conditions,
                        values["filter_match"],
                        values["header"],
                    ),
                )

            self.form(command, fields, filter_data)
        elif command == "find":

            def find(values):
                found = find_next_match(
                    self.session.workbook,
                    values["query"],
                    (self.sheet_index, *self.grid.cursor),
                    None if values["whole_workbook"] else sheet,
                    values["case_sensitive"],
                    values["whole_cell"],
                    "values" if values["search_values"] else "raw",
                )
                if found["position"] is None:
                    raise ValueError(self.text("nothing_found"))
                self.sheet_index, r, c = found["position"]
                self.grid.top = self.grid.left = 0
                self.refresh_workbook()
                self.grid.move(r, c)
                self.tabs.active = f"sheet-{self.sheet_index}"
                self.notify(f"{found['index']}/{found['total']}")

            self.form(
                command,
                [
                    Field("query"),
                    Field("case_sensitive", False),
                    Field("whole_cell", False),
                    Field("search_values", False),
                    Field("whole_workbook", False),
                ],
                find,
            )
        elif command == "replace":
            self.form(
                command,
                [
                    Field("query"),
                    Field("replacement"),
                    Field("case_sensitive", False),
                    Field("whole_cell", False),
                    Field("whole_workbook", False),
                ],
                lambda v: self.mutate(
                    command,
                    lambda w: replace_matches(
                        w,
                        v["query"],
                        v["replacement"],
                        None if v["whole_workbook"] else sheet,
                        case_sensitive=v["case_sensitive"],
                        whole_cell=v["whole_cell"],
                    ),
                ),
            )
        elif command == "trace_formula":
            trace = trace_dependencies(self.session.workbook, sheet, address(*self.grid.cursor))
            lines = [
                f"{trace['sheet']}!{trace['cell']}",
                self.text("direct_references"),
                "",
                self.text("precedents"),
            ]
            lines.extend(f"  {item['sheet']}!{item['range']}" for item in trace["precedents"])
            lines.extend(["", self.text("dependents")])
            lines.extend(f"  {item['sheet']}!{item['cell']}" for item in trace["dependents"])
            lines.extend(trace["unresolved"])
            if trace["truncated"]:
                lines.append(self.text("results_truncated"))
            self.show_text(command, "\n".join(lines))
        else:
            row, column = self.grid.cursor
            span = (
                self.grid.sheet.used_range
                if command == "select_all"
                else CellRange(row, 0, row, MAX_COLUMNS - 1)
                if command == "select_row"
                else CellRange(0, column, MAX_ROWS - 1, column)
            )
            self.grid.select_extent(span)
