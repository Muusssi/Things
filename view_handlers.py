
import random

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

class GuessHandler(BaseHandler):

    def handle_answers(self, guess_id):
        question_ids = self.get_arguments('question')
        self.db.record_guess_success(guess_id, len(question_ids))
        for question_id in question_ids:
            answer = self.get_argument('answer_' + question_id, None)
            if int(question_id) == 0:
                continue
            if answer:
                self.db.answer(guess_id, question_id, answer)

    def answers_so_far(self, question_dict):
        answers_so_far = []
        wrong_guesses = [int(x) for x in self.get_arguments('wrong_guess')]
        for question_id in self.get_arguments('question')[::-1]:
            question_id = int(question_id)
            answer = self.get_argument(f'answer_{question_id}', None)
            if question_id == 0:
                guess_id = int(self.get_argument('guess_id'))
                if answer == 'no':
                    wrong_guesses.append(guess_id)
                continue

            answered_question = question_dict[question_id]
            answered_question['answer'] = answer
            answers_so_far.append(answered_question)
            del question_dict[question_id]
        return answers_so_far, wrong_guesses

    def correct_guess_made(self):
        if '0' in self.get_arguments('question'):
            if self.get_argument('answer_0', None) == 'yes':
                return True
        return False

    def answer_given(self):
        if self.get_argument('thing', None):
            return True
        return False

    def get(self):
        if self.correct_guess_made():
            guess_id = int(self.get_argument('guess_id'))
            self.handle_answers(guess_id)
            self.redirect('/guess')
            return
        if self.answer_given():
            thing_id = self.db.reqister_thing(self.get_argument('thing'))
            self.handle_answers(thing_id)
            self.redirect('/guess')
            return
        out_of_questions = False
        question_dict = self.db.question_dict()
        answers_so_far, wrong_guesses = self.answers_so_far(question_dict)
        things = self.db.matching_things(answers_so_far, wrong_guesses)
        if things and things[0]['diff'] < things[1]['diff']:
            answers_so_far.append({'question': f"Is it {things[0]['name']}?", 'id': 0})
        elif things:
            relevant_questions = self.db.relevant_questions(things[:5], answers_so_far)
            if relevant_questions:
                answers_so_far.append(random.choice(relevant_questions[:min(3, len(relevant_questions))]))
            else:
                out_of_questions = True
        elif question_dict:
            answers_so_far.append(random.choice(list(question_dict.values())))
        self.render('guess.html',
                    things=things,
                    wrong_guesses=wrong_guesses,
                    answers_so_far=answers_so_far[::-1],
                    out_of_questions=out_of_questions)

    post = get


URLS = (
    url(r"/", MainHandler),
    url(r"/teach/?$", TeachHandler),
    url(r"/teach/missing/?$", TeachMissingHandler),
    url(r"/question/new/?$", NewQuestionHandler),
    url(r"/network/?$", NetworkHandler),
    url(r"/guess/?$", GuessHandler),
)
