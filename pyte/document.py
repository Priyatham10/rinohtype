
import time
import pickle

from .dimension import PT
from .paper import Paper
from .layout import Container, EndOfPage
from .backend import pdf
from .warnings import warn


PORTRAIT = 'portrait'
LANDSCAPE = 'landscape'


class Page(Container):
    def __init__(self, document, paper, orientation=PORTRAIT):
        assert isinstance(document, Document)
        assert isinstance(paper, Paper)
        self._document = document
        self.paper = paper
        self.orientation = orientation
        if self.orientation is PORTRAIT:
            width = self.paper.width
            height = self.paper.height
        else:
            width = self.paper.height
            height = self.paper.width
        super().__init__(None, 0*PT, 0*PT, width, height)
        self.backend = self.document.backend
        self.section = None

    @property
    def page(self):
        return self

    @property
    def document(self):
        return self._document

    @property
    def canvas(self):
        return self.backend_page.canvas

    def render(self):
        backend_document = self.document.backend_document
        self.backend_page = self.backend.Page(self, backend_document,
                                              self.width, self.height)
        end_of_page = None
        try:
            super().render()
        except EndOfPage as e:
            end_of_page = e

        for child in self.children:
            child.place()

        if end_of_page is not None:
            raise end_of_page

    def place(self):
        pass


class Document(object):
    cache_extension = '.ptc'

    def __init__(self, parser, filename, backend=pdf):
        self.xml = parser.parse(filename)
        self.root = self.xml.getroot()

        self.creator = "pyTe"
        self.author = None
        self.title = None
        self.keywords = []
        self.created = time.asctime()

        self.backend = backend
        self.backend_document = self.backend.Document(self, self.title)
        self.counters = {}
        self.elements = {}
        self._unique_id = 0

    @property
    def unique_id(self):
        self._unique_id += 1
        return self._unique_id

    def load_cache(self, filename):
        try:
            file = open(filename + self.cache_extension, 'rb')
            self.number_of_pages, self.page_references = pickle.load(file)
            self._previous_number_of_pages = self.number_of_pages
            self._previous_page_references = self.page_references.copy()
            file.close()
        except IOError:
            self.number_of_pages = 0
            self._previous_number_of_pages = -1
            self.page_references = {}
            self._previous_page_references = {}

    def save_cache(self, filename):
        file = open(filename + self.cache_extension, 'wb')
        data = (self.number_of_pages, self.page_references)
        pickle.dump(data, file)
        file.close()

    def add_page(self, page, number):
        assert isinstance(page, Page)
        self.pages.append(page)
        page.number = number

    def has_converged(self):
        return (self.number_of_pages == self._previous_number_of_pages and
                self.page_references == self._previous_page_references)

    def render(self, filename):
        self.load_cache(filename)
        self.number_of_pages = self.render_loop()
        while not self.has_converged():
            self._previous_number_of_pages = self.number_of_pages
            self._previous_page_references = self.page_references.copy()
            print('Not yet converged, rendering again...')
            del self.backend_document
            self.backend_document = self.backend.Document(self, self.title)
            self.number_of_pages = self.render_loop()
        self.save_cache(filename)
        print('Writing output: {}'.format(filename +
                                          self.backend_document.extension))
        self.backend_document.write(filename)

    def render_loop(self):
        self.pages = []
        self.setup()
        index = 0
        while index < len(self.pages):
            page = self.pages[index]
            index += 1
            try:
                page.render()
            except EndOfPage as e:
                self.add_to_chain(e.args[0])
        return len(self.pages)

    def setup(self):
        raise NotImplementedError

    def add_to_chain(self, chain):
        raise NotImplementedError


class DocumentElement(object):
    def __init__(self, parent=None):
        self.parent = parent

    @property
    def page(self):
        return self.parent.page

    @property
    def document(self):
        return self.parent.document

    def warn(self, message):
        if hasattr(self, '_source'):
            message = '[{}] {}'.format(self._source.location, message)
        warn(message)
