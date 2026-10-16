from rich.segment import Segment
from rich.style import Style
from textual.strip import Strip
from textual.widgets import Input


def safe_text(value, multiline=False):
    """원문을 바꾸지 않고 터미널 제어 문자를 가시 문자로 표시한다."""
    output = []
    for character in str(value):
        code = ord(character)
        if character == "\n" and multiline:
            output.append(character)
        elif code < 32:
            output.append(chr(0x2400 + code))
        elif code == 127:
            output.append("␡")
        elif 128 <= code <= 159:
            output.append("�")
        else:
            output.append(character)
    return "".join(output)


class SafeInput(Input):
    def render_line(self, y):
        line = super().render_line(y)
        segments = [
            Segment(safe_text(segment.text), segment.style or Style(), segment.control)
            if not segment.control
            else segment
            for segment in line
        ]
        return Strip(segments).adjust_cell_length(line.cell_length)
