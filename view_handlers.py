
from tornado.web import url
from psycopg2 import IntegrityError

from base_handler import BaseHandler

class MainHandler(BaseHandler):
    def get(self):
        self.render('main.html',
                    learned_things_count=self.db.learned_things_count(),
                    question_count=self.db.question_count(),
                    answer_count=self.db.answer_count())

class TeachHandler(BaseHandler):

    def get(self):
        thing_offset = int(self.get_argument('offset', 0))
        self.render('teach.html',
                    thing_offset=thing_offset,
                    thing_name=self.get_argument('thing', None),
                    thing=self.db.things()[thing_offset],
                    questions=self.db.questions())

    def handle_answer(self):
        thing_id = self.db.reqister_thing(self.get_argument('thing'))
        for question_id in self.get_arguments('question'):
            answer = self.get_argument('answer_' + question_id, None)
            if answer:
                self.db.answer(thing_id, question_id, answer)

    def post(self):
        self.handle_answer()
        self.redirect('/teach')

class TeachMissingHandler(TeachHandler):

    def get(self):
        thing_offset = int(self.get_argument('offset', 0))
        things = self.db.things_missing_answers()
        if len(things) > thing_offset:
            self.render('teach_missing.html',
                        thing_offset=thing_offset,
                        thing_name=None,
                        thing=things[thing_offset],
                        questions=self.db.questions())
        else:
            self.redirect('/teach')

    def post(self):
        self.handle_answer()
        self.redirect('/teach/missing')


class NetworkHandler(BaseHandler):
    def get(self):
        self.render('network.html')

class NewQuestionHandler(BaseHandler):

    def render_form(self, message='', error=''):
        self.render('new_question.html',
                    indistinguishable=self.db.indistinguishable(),
                    questions=self.db.questions(),
                    message=message, error=error)

    def get(self):
        self.render_form()

    def post(self):
        try:
            self.db.new_question(self.get_argument('question'))
        except IntegrityError:
            self.render_form(error='Question already exists.')
            return
        self.render_form(message='New question added.')


URLS = (
    url(r"/", MainHandler),
    url(r"/teach/?$", TeachHandler),
    url(r"/teach/missing/?$", TeachMissingHandler),
    url(r"/question/new/?$", NewQuestionHandler),
    url(r"/network/?$", NetworkHandler),
)