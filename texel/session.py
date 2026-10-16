from __future__ import annotations

from copy import deepcopy

from .formula import Evaluator
from .model import Workbook
from .store import ConflictError, Store


class Session:
    def __init__(self, path, source="tui"):
        self.store = Store(path)
        self.source = source
        self.reload()

    def reload(self):
        self.workbook, self.revision = self.store.load()
        self.evaluator = Evaluator(self.workbook)

    def sync(self):
        if self.store.revision != self.revision:
            self.reload()
            return True
        return False

    def apply(self, label, mutation, expected_revision=None):
        candidate, evaluator, result, expected = self._prepare(mutation, expected_revision)
        revision = self.store.commit(self.workbook, candidate, expected, label, self.source)
        self.workbook, self.revision, self.evaluator = candidate, revision, evaluator
        return result

    def preview(self, mutation, expected_revision=None):
        candidate, _evaluator, result, expected = self._prepare(mutation, expected_revision)
        actual = self.store.revision
        if actual != expected:
            raise ConflictError(expected, actual)
        return candidate, result

    def _prepare(self, mutation, expected_revision):
        expected = self.revision if expected_revision is None else expected_revision
        if expected != self.revision:
            raise ConflictError(expected, self.revision)
        copies = {}
        candidate = deepcopy(self.workbook, copies)
        result = mutation(candidate)
        candidate.validate()
        evaluator = Evaluator(candidate)
        for old in self.workbook.sheets:
            if not old.protected:
                continue
            sheet = copies[id(old)]
            if not any(sheet is current for current in candidate.sheets):
                raise ValueError("Unprotect the sheet before deleting it")
            for (r, c), previous in old.cells.items():
                if previous.locked and previous != sheet.cell(r, c, False):
                    raise ValueError(f"Cell {r + 1},{c + 1} is protected")
        for index, sheet in enumerate(candidate.sheets):
            for (r, c), cell in sheet.cells.items():
                rule = cell.validation
                if rule is not None and not rule.check(evaluator.value(index, r, c)):
                    raise ValueError(f"Cell {r + 1},{c + 1} violates its validation rule")
        return candidate, evaluator, result, expected

    def undo(self, expected_revision=None):
        changed = self.store.navigate_history(
            self.revision if expected_revision is None else expected_revision
        )
        if changed:
            self.reload()
        return changed

    def redo(self, expected_revision=None):
        changed = self.store.navigate_history(
            self.revision if expected_revision is None else expected_revision, True
        )
        if changed:
            self.reload()
        return changed


__all__ = ["Session", "ConflictError", "Workbook"]
