"""
Base classes for flowable and floating document elements. These are elements
that make up the content of a document and are rendered onto its pages.

* :class:`Flowable`: Element that is rendered onto a :class:`Container`.
* :class:`FlowableStyle`: Style class specifying the vertical space surrounding
                          a :class:`Flowable`.
* :class:`Floating`: Decorator to transform a :class:`Flowable` into a floating
                     element.
"""


from .layout import EndOfContainer
from .style import Style, Styled
from .util import Decorator


__all__ = ['Flowable', 'FlowableStyle', 'Floating']


class FlowableException(Exception):
    pass


class FlowableStyle(Style):
    """The :class:`Style` for :class:`Flowable` objects. It has the following
    attributes:

    * `space_above`: Vertical space preceding the flowable (:class:`Dimension`)
    * `space_below`: Vertical space following the flowable (:class:`Dimension`)
    """

    attributes = {'space_above': 0,
                  'space_below': 0}


class Flowable(Styled):
    """An element that can be 'flowed' into a :class:`Container`. A flowable can
    adapt to the width of the container, or it can horizontally align itself in
    the container."""

    style_class = FlowableStyle

    def __init__(self, style=None, parent=None):
        """Initialize this flowable and associate it with the given `style` and
        `parent` (see :class:`Styled`)."""
        super().__init__(style, parent)
        self.resume = False

    def flow(self, container):
        """Flow this flowable into `container` and return the vertical space
        consumed.

        The flowable's contents is preceded by a vertical space with a height
        as specified in its style's `space_above` attribute. Similarly, the
        flowed content is followed by a vertical space with a height given
        by the `space_below` style attribute."""
        start_offset = container.cursor
        if not self.resume:
            self.resume = True
            container.advance(float(self.get_style('space_above')))
        self.render(container)
        self.resume = False
        try:
            container.advance(float(self.get_style('space_below')))
        except EndOfContainer:
            pass
        return container.cursor - start_offset

    @property
    def width(self):
        raise FlowableException

    def spans(self):
        yield self

    def render(self, container):
        """Renders the flowable's content to `container`. This is different for
        each type of flowable."""
        raise NotImplementedError


class Floating(Decorator):
    """Decorator to transform a :class:`Flowable` into a floating element. A
    floating element or 'float' is not flowed into its designated container, but
    is forwarded to another container, pointed to by the former's
    :attr:`Container.float_space` attribute.

    This is typically used to place figures and tables at the top or bottom of a
    page, instead of in between paragraphs."""

    def flow(self, container):
        """Flow this flowable into the float space associated with `container`.
        """
        super().flow(container.float_space)
        return 0
