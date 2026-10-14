"""Cairo charts and the progress ring, drawn in each section's gradient."""
import calendar
import math
from datetime import date, timedelta

import cairo
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Graphene", "1.0")
from gi.repository import Gdk, GLib, Graphene, Gtk

from .theme import Theme

LOW, MID, HIGH = (0.85, 0.33, 0.30), (0.93, 0.69, 0.25), (0.25, 0.68, 0.42)


def score_color(percent: float) -> tuple[float, float, float]:
    t = max(0.0, min(percent, 100.0)) / 50
    start, end = (LOW, MID) if t < 1 else (MID, HIGH)
    t = t if t < 1 else t - 1
    return tuple(a + (b - a) * t for a, b in zip(start, end))


class Chart(Gtk.Widget):
    """Base class: subclasses implement paint(). Drawn with pycairo into a texture, so the python3-gi-cairo bridge is not needed."""

    def __init__(self, height: int, theme: Theme):
        super().__init__(hexpand=True)
        self.theme = theme
        self._texture = None
        self._texture_key = None
        self.set_size_request(-1, height)

    def set_content_height(self, height: int) -> None:
        self.set_size_request(self.get_size_request()[0], height)

    def set_content_width(self, width: int) -> None:
        self.set_size_request(width, self.get_size_request()[1])

    def queue_draw(self) -> None:
        self._texture = None
        super().queue_draw()

    def do_snapshot(self, snapshot):
        width, height, scale = self.get_width(), self.get_height(), self.get_scale_factor()
        fg = self.get_color()
        key = (width, height, scale, fg.red, fg.green, fg.blue)
        if width <= 0 or height <= 0:
            return
        if self._texture is None or self._texture_key != key:
            self._texture, self._texture_key = self._render(width, height, scale, (fg.red, fg.green, fg.blue)), key
        snapshot.append_texture(self._texture, Graphene.Rect().init(0, 0, width, height))

    def _render(self, width: int, height: int, scale: int, fg) -> Gdk.MemoryTexture:
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width * scale, height * scale)
        surface.set_device_scale(scale, scale)
        cr = cairo.Context(surface)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        self.paint(cr, width, height, fg)
        surface.flush()
        return Gdk.MemoryTexture.new(width * scale, height * scale, Gdk.MemoryFormat.B8G8R8A8_PREMULTIPLIED, GLib.Bytes.new(bytes(surface.get_data())), surface.get_stride())

    def paint(self, cr, width, height, fg):
        raise NotImplementedError

    def fade(self, top: float, bottom: float, alpha: float = 0.35) -> cairo.LinearGradient:
        gradient = cairo.LinearGradient(0, top, 0, bottom)
        gradient.add_color_stop_rgba(0, *self.theme.start_rgb, alpha)
        gradient.add_color_stop_rgba(1, *self.theme.start_rgb, 0.0)
        return gradient

    def gradient(self, x0, y0, x1, y1, alpha=1.0) -> cairo.LinearGradient:
        gradient = cairo.LinearGradient(x0, y0, x1, y1)
        gradient.add_color_stop_rgba(0, *self.theme.start_rgb, alpha)
        gradient.add_color_stop_rgba(1, *self.theme.end_rgb, alpha)
        return gradient


def _text(cr, fg, text, x, y, size=12, align="left", alpha=0.8):
    cr.set_font_size(size)
    extents = cr.text_extents(text)
    x -= extents.width if align == "right" else extents.width / 2 if align == "center" else 0
    cr.set_source_rgba(*fg, alpha)
    cr.move_to(x, y)
    cr.show_text(text)


def _rounded(cr, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


class Ring(Chart):
    """Circular progress with a big percentage in the middle."""

    def __init__(self, theme: Theme, size: int = 150, on_gradient: bool = False):
        super().__init__(size, theme)
        self.set_content_width(size)
        self.set_hexpand(False)
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)
        self._percent: float | None = None
        self._caption = ""
        self._white = (1.0, 1.0, 1.0) if on_gradient else None

    def update(self, percent: float | None, caption: str = "") -> None:
        self._percent, self._caption = percent, caption
        self.queue_draw()

    def paint(self, cr, width, height, fg):
        cx, cy, line = width / 2, height / 2, width * 0.11
        radius = width / 2 - line
        cr.set_line_width(line)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_source_rgba(*(self._white or fg), 0.2)
        cr.arc(cx, cy, radius, 0, 2 * math.pi)
        cr.stroke()
        if self._percent:
            cr.set_source_rgb(*self._white) if self._white else cr.set_source(self.gradient(0, 0, width, height))
            cr.arc(cx, cy, radius, -math.pi / 2, -math.pi / 2 + 2 * math.pi * min(self._percent, 100) / 100)
            cr.stroke()
        color = self._white or fg
        _text(cr, color, "-" if self._percent is None else f"{self._percent:.0f}%", cx, cy + width * 0.06, width * 0.22, "center", 1.0)
        _text(cr, color, self._caption, cx, cy + width * 0.22, width * 0.085, "center", 0.65)


class HBars(Chart):
    """Horizontal bars: rows of (label, value, text shown at the end)."""
    ROW = 32

    def __init__(self, theme: Theme):
        super().__init__(self.ROW, theme)
        self._rows: list[tuple[str, float, str]] = []
        self._max = 100.0

    def update(self, rows: list[tuple[str, float, str]], max_value: float = 100.0) -> None:
        self._rows, self._max = rows, max(max_value, 1e-9)
        self.set_content_height(max(self.ROW, self.ROW * len(rows)))
        self.queue_draw()

    def paint(self, cr, width, height, fg):
        label_w, value_w = 110, 64
        bar_w = max(width - label_w - value_w, 1)
        for i, (label, value, text) in enumerate(self._rows):
            y = i * self.ROW
            _text(cr, fg, label, 0, y + 21, 12)
            cr.set_source_rgba(*fg, 0.09)
            _rounded(cr, label_w, y + 8, bar_w, 16, 8)
            cr.fill()
            if value > 0:
                cr.set_source(self.gradient(label_w, 0, label_w + bar_w, 0))
                _rounded(cr, label_w, y + 8, max(bar_w * min(value / self._max, 1), 16), 16, 8)
                cr.fill()
            _text(cr, fg, text, width, y + 21, 12, "right", 0.95)


class ColumnChart(Chart):
    """Vertical bars with labels underneath and an optional dashed goal line."""

    def __init__(self, theme: Theme, height: int = 170, unit: str = ""):
        super().__init__(height, theme)
        self._labels: list[str] = []
        self._values: list[float | None] = []
        self._goal: float | None = None
        self._max = 100.0
        self._unit = unit

    def update(self, labels: list[str], values: list[float | None], goal: float | None = None, max_value: float | None = None) -> None:
        self._labels, self._values, self._goal = labels, values, goal
        self._max = max_value or max([v for v in values if v] + [goal or 0, 1]) * 1.1
        self.queue_draw()

    def paint(self, cr, width, height, fg):
        n = max(len(self._values), 1)
        slot, base, top = width / n, height - 22, 16
        plot = base - top
        for i, (label, value) in enumerate(zip(self._labels, self._values)):
            x = i * slot + slot * 0.2
            cr.set_source_rgba(*fg, 0.07)
            _rounded(cr, x, top, slot * 0.6, plot, 8)
            cr.fill()
            if value:
                h = max(plot * min(value / self._max, 1), 8)
                cr.set_source(self.gradient(0, top + plot - h, 0, base))
                _rounded(cr, x, base - h, slot * 0.6, h, 8)
                cr.fill()
                if n <= 10:
                    _text(cr, fg, f"{value:.0f}{self._unit}", x + slot * 0.3, base - h - 4, 10, "center", 0.9)
            _text(cr, fg, label, x + slot * 0.3, height - 6, 10, "center", 0.65)
        if self._goal:
            y = base - plot * self._goal / self._max
            cr.set_source_rgba(*fg, 0.55)
            cr.set_dash([4, 4])
            cr.set_line_width(1)
            cr.move_to(0, y)
            cr.line_to(width, y)
            cr.stroke()
            cr.set_dash([])


class LineChart(Chart):
    """A line over the days of a period, with a soft filled area and optional goal line."""
    PAD = 38

    def __init__(self, theme: Theme, height: int = 190):
        super().__init__(height, theme)
        self._points: dict[date, float] = {}
        self._first = self._last = date.today()
        self._low, self._high = 0.0, 100.0
        self._goal: float | None = None

    def update(self, points: dict[date, float], first: date, last: date, goal: float | None = None, bounds: tuple[float, float] | None = None) -> None:
        self._points, self._first, self._last, self._goal = points, first, last, goal
        if bounds:
            self._low, self._high = bounds
        else:
            values = list(points.values()) + ([goal] if goal else [])
            low, high = (min(values), max(values)) if values else (0, 1)
            pad = max((high - low) * 0.25, 0.5)
            self._low, self._high = low - pad, high + pad
        self.queue_draw()

    def paint(self, cr, width, height, fg):
        left, bottom = self.PAD, height - 22
        plot_w, plot_h = width - left - 10, bottom - 10
        span = max((self._last - self._first).days, 1)

        def point(day, value):
            x = left + plot_w * (day - self._first).days / span
            return x, bottom - plot_h * (value - self._low) / (self._high - self._low or 1)

        for fraction in (0, 0.5, 1):
            value = self._low + (self._high - self._low) * fraction
            _text(cr, fg, f"{value:.0f}" if self._high - self._low > 20 else f"{value:.1f}", left - 6, bottom - plot_h * fraction + 4, 10, "right", 0.6)
        step = 1 if span <= 7 else 5
        for offset in range(0, span + 1, step):
            day = self._first + timedelta(days=offset)
            _text(cr, fg, f"{day.day}", point(day, self._low)[0], height - 6, 10, "center", 0.6)
        if self._goal is not None:
            cr.set_source_rgba(*fg, 0.5)
            cr.set_dash([4, 4])
            cr.set_line_width(1)
            cr.move_to(*point(self._first, self._goal))
            cr.line_to(*point(self._last, self._goal))
            cr.stroke()
            cr.set_dash([])
        points = [point(day, value) for day, value in sorted(self._points.items())]
        if not points:
            return
        cr.move_to(points[0][0], bottom)
        for p in points:
            cr.line_to(*p)
        cr.line_to(points[-1][0], bottom)
        cr.close_path()
        cr.set_source(self.fade(10, bottom))
        cr.fill()
        cr.set_source(self.gradient(left, 0, width, 0))
        cr.set_line_width(3)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        for i, p in enumerate(points):
            cr.line_to(*p) if i else cr.move_to(*p)
        cr.stroke()
        for x, y in points:
            cr.set_source_rgb(*self.theme.end_rgb)
            cr.arc(x, y, 4.5, 0, 2 * math.pi)
            cr.fill()


class Heatmap(Chart):
    """Calendar grid where each day is colored by its score."""
    HEADER = 18
    CELL = 52

    def __init__(self, theme: Theme):
        super().__init__(self.HEADER + 6 * self.CELL, theme)
        self._daily: dict[date, float] = {}
        self._year, self._month = date.today().year, date.today().month

    def update(self, daily: dict[date, float], year: int, month: int) -> None:
        self._daily, self._year, self._month = daily, year, month
        self.queue_draw()

    def paint(self, cr, width, height, fg):
        cell = min(width / 7, self.CELL)
        left = (width - 7 * cell) / 2
        for col, name in enumerate(calendar.day_abbr):
            _text(cr, fg, name, left + col * cell + cell / 2 - 2, 12, 10, "center", 0.6)
        for row, week in enumerate(calendar.Calendar().monthdayscalendar(self._year, self._month)):
            for col, day in enumerate(week):
                if day:
                    self._cell(cr, fg, left + col * cell, self.HEADER + row * cell, cell - 4, day)

    def _cell(self, cr, fg, x, y, size, day):
        score = self._daily.get(date(self._year, self._month, day))
        if score is None:
            cr.set_source_rgba(*fg, 0.07)
        else:
            cr.set_source_rgb(*score_color(score))
        _rounded(cr, x, y, size, size, 10)
        cr.fill()
        _text(cr, (0.05, 0.07, 0.12) if score is not None else fg, str(day), x + size / 2, y + size / 2 + 4, 11, "center", 0.95)
