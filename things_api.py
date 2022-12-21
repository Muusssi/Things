
from tornado.web import url
#from tornado_swagger.model import register_swagger_model

from base_handler import BaseHandler


class BaseDataHandler(BaseHandler):
    def get(self):
        # Redirect api base queries to API doc
        self.redirect('/data/doc')

class ThingsDataHandler(BaseDataHandler):
    def get(self):
        """
          ---
          tags:
          - Things
          summary: List things
          description: Lists all known things ordered by number of answers received so far
          produces:
          - application/json
          responses:
            200:
              schema:
                type: object
                properties:
                  things:
                    type: array
                    items:
                      type: object
                      properties:
                        id:
                          type: integer
                        name:
                          type: string
                        answer_count:
                          type: integer
        """
        self.write({'things': self.db.things()})


class QuestionsDataHandler(BaseDataHandler):
    def get(self):
        """
          ---
          tags:
          - Questions
          summary: List questions
          description: Lists all known registered questions
          produces:
          - application/json
          responses:
            200:
              schema:
                type: object
                properties:
                  questions:
                    type: array
                    items:
                      type: object
                      properties:
                        id:
                          type: integer
                        question:
                          type: string
        """
        self.write({'questions': self.db.questions()})


class NetworkDataHandler(BaseDataHandler):
    def get(self):
        """
          ---
          tags:
          - Network
          summary: Network visualisation data
          description: Data used to form the network visualisation
          produces:
          - application/json
          responses:
            200:
              schema:
                type: object
                properties:
                  things:
                    type: array
                    items:
                      type: object
                      properties:
                        id:
                          type: integer
                        label:
                          type: string
                        updated_recently:
                          type: boolean
                  links:
                    type: array
                    items:
                      type: object
                      properties:
                        from:
                          type: integer
                        to:
                          type: integer
                        length:
                          type: number
        """
        max_diff = float(self.get_argument('max_diff', 0.1))
        min_links = int(self.get_argument('min_links', 1))
        things, links = self.db.network_data(max_diff, min_links)
        self.write({'things': things, 'links': links})


class TeachDataHandler(BaseDataHandler):
    def post(self):
        """
          ---
          tags:
          - Teach
          summary: Teach system by feeding answers to questions about things
          description:
          parameters:
          - name: thing
            in: query
            description: Name of the thing
            required: true
            type: string
          - name: question
            in: query
            description: Id of the question
            required: true
            type: integer
          - name: answer
            in: query
            description: The answer
            required: true
            type: string
            enum:
              - 'yes'
              - 'no'
              - 'maybe'
          responses:
            201:
              -
        """
        thing_id = self.db.reqister_thing(self.get_argument('thing'))
        question_id = self.get_argument('question')
        answer = self.get_argument('answer')
        self.db.answer(thing_id, question_id, answer)
        self.set_status(201)


API_URLS = (
    url(r"/data/?$", BaseDataHandler),
    url(r"/data/network/?$", NetworkDataHandler),
    url(r"/data/things/?$", ThingsDataHandler),
    url(r"/data/questions/?$", QuestionsDataHandler),
    url(r"/data/teach/?$", TeachDataHandler),
)
