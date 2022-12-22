
import psycopg2

THINGS_BY_ANSWERS = """
SELECT id, name, answers
FROM (
    SELECT thing.id, thing.name, count(answer.answer) as answers
    FROM thing
    LEFT OUTER JOIN answer ON thing.id=answer.thing
    GROUP BY thing.id, thing.name
) AS foo
ORDER BY answers
"""

MISSING_ANSWERS = """
SELECT id, name, array_agg(question_id), count(*) as missing
FROM (
    SELECT thing.id, thing.name, question.id as question_id, count(answer.answer) as answers
    FROM thing
    CROSS JOIN question
    FULL OUTER JOIN answer ON thing.id=answer.thing
                          AND question.id=answer.question
    WHERE thing.id IN (SELECT DISTINCT thing FROM answer)
    GROUP BY thing.id, thing.name, question.id
    ORDER BY thing.id, thing.name, question.id
) AS foo
WHERE answers=0
GROUP BY id, name
ORDER BY missing DESC;
"""

COLLECTED_ANSWERS = """
SELECT thing, question,
       (COUNT(nullif(answer='yes', false)) + COUNT(nullif(answer='sometimes', false))::real/2)/COUNT(*) as yes,
       (COUNT(nullif(answer='no', false)) + COUNT(nullif(answer='sometimes', false))::real/2)/COUNT(*) as no,
       COUNT(nullif(answer='sometimes', false))/COUNT(*) as sometimes,
       max(answer.timestamp)>now()-'12h'::interval as updated_recently
FROM answer
GROUP BY thing, question
ORDER BY thing, question
"""

INDISTINGUISHABLE = """
WITH collected_answers AS (
    {collected_answers}
)
SELECT thing_a, thing_b, difference
FROM (
    SELECT thing_a.name as thing_a, thing_b.name as thing_b, COUNT(*) as count,
           sum(ABS(ans_a.yes - ans_b.yes)) + sum(ABS(ans_a.no - ans_b.no)) as difference
    FROM collected_answers as ans_a
    JOIN collected_answers as ans_b ON ans_a.thing<ans_b.thing
                                   AND ans_a.question=ans_b.question
    JOIN thing as thing_a ON ans_a.thing=thing_a.id
    JOIN thing as thing_b ON ans_b.thing=thing_b.id
    JOIN question ON ans_a.question=question.id
    GROUP BY thing_a.name, thing_b.name
    ORDER BY difference, thing_a.name, thing_b.name
) AS differences
WHERE difference<3 AND count>15
ORDER BY difference;
""".format(collected_answers=COLLECTED_ANSWERS)

SIMILAR_THINGS = """
WITH collected_answers AS (
    {collected_answers}
)
SELECT thing_a, id_a, thing_b, id_b, difference, rank, updated_recently
    FROM (
    SELECT thing_a, id_a, thing_b, id_b, difference::real/count as difference,
           RANK() OVER(PARTITION BY thing_a ORDER BY difference) AS rank,
           updated_recently
    FROM (
        SELECT thing_a.name as thing_a, thing_a.id as id_a, thing_b.name as thing_b, thing_b.id as id_b, COUNT(*) as count,
               sum(ABS(ans_a.yes - ans_b.yes)) + sum(ABS(ans_a.no - ans_b.no)) as difference,
               bool_or(ans_a.updated_recently) as updated_recently
        FROM collected_answers as ans_a
        JOIN collected_answers as ans_b ON ans_a.thing<ans_b.thing
                                       AND ans_a.question=ans_b.question
        JOIN thing as thing_a ON ans_a.thing=thing_a.id
        JOIN thing as thing_b ON ans_b.thing=thing_b.id
        JOIN question ON ans_a.question=question.id
        GROUP BY thing_a.name, thing_a.id, thing_b.name, thing_b.id
        ORDER BY difference, thing_a.name, thing_b.name
    ) AS differences
    WHERE count>{min_answers}
) AS foo
WHERE (rank<={min_links} OR difference<{max_diff}) AND difference<0.5
ORDER BY id_a, rank;
"""


MATCHING_THINGS = """
WITH collected_answers AS (
    {collected_answers}
),
answers_so_far(thing, question, yes, no) AS (
    VALUES
    {values}
)
SELECT thing.id, thing.name,
       (sum(ABS(known_answers.yes - answers_so_far.yes)) +
        sum(ABS(known_answers.no - answers_so_far.no)))::real/count(*) as difference
FROM thing
JOIN (
    SELECT thing, question, yes, no
    FROM collected_answers
) known_answers ON known_answers.thing=thing.id
JOIN answers_so_far ON answers_so_far.question=known_answers.question
{filter_things}
GROUP BY thing.id, thing.name
ORDER BY difference;
"""

RELEVANT_QUESTIONS = """
SELECT question.question, question.id,
       abs((yes - count)*(no - count)*(sometimes - count)) as relevance
FROM (
    SELECT question,
           count(nullif(answer='yes', false)) as yes,
           count(nullif(answer='no', false)) as no,
           count(nullif(answer='sometimes', false)) as sometimes,
           count(*) as count
    FROM answer
    {filterer}
    GROUP BY question
) AS answers
JOIN question ON answers.question=question.id
ORDER BY relevance DESC;
"""


class Database():

    def __init__(self, config):
        self.config = config
        self._connect()

    def _connect(self):
        self._conn = psycopg2.connect(
            dbname=self.config['database'],
            user=self.config['user'],
            password=self.config['password'],
            host=self.config['host'],
        )
        self._conn.autocommit = True

    def _cursor(self):
        return self._conn.cursor()

    def _commit(self):
        self._conn.commit()

    def _close_connection(self):
        self._conn.close()

    def reconnect(self):
        self._close_connection()
        self._connect()

    def execute_and_get_rows(self, sql, values=None):
        cur = self._cursor()
        cur.execute(sql, values)
        return list(cur.fetchall())

    def execute(self, sql, values=None, return_row=False):
        cur = self._cursor()
        cur.execute(sql, values)
        if return_row:
            return cur.fetchone()

    def questions(self):
        sql = "SELECT id, question FROM question ORDER BY id;"
        questions = []
        for question_id, question in self.execute_and_get_rows(sql):
            questions.append({'id': question_id, 'question': question})
        return questions

    def question_dict(self):
        return {question['id']: question for question in self.questions()}

    def things(self):
        things = []
        for thing_id, name, answer_count in self.execute_and_get_rows(THINGS_BY_ANSWERS):
            things.append({'id': thing_id, 'name': name, 'answer_count': answer_count})
        return things

    def things_missing_answers(self):
        things = []
        for thing_id, name, questions, _ in self.execute_and_get_rows(MISSING_ANSWERS):
            things.append({'id': thing_id, 'name': name, 'questions': questions})
        return things

    def new_question(self, question):
        sql = "INSERT INTO question(question) VALUES (%s)"
        self.execute(sql, (question,))

    def reqister_thing(self, thing):
        sql = "INSERT INTO thing(name) VALUES (%s) ON CONFLICT DO NOTHING RETURNING id;"
        row = self.execute(sql, (thing,), return_row=True)
        if not row:
            sql = "SELECT id FROM thing WHERE name=%s"
            row = self.execute(sql, (thing,), return_row=True)
        return row[0]

    def answer(self, thing, question, answer):
        sql = "INSERT INTO answer(thing, question, answer) VALUES (%s,%s,%s)"
        self.execute(sql, (thing, question, answer))

    def indistinguishable(self):
        return self.execute_and_get_rows(INDISTINGUISHABLE)

    def answer_count(self):
        sql = "SELECT count(*) FROM answer"
        (answer_count,) = self.execute(sql, return_row=True)
        return answer_count

    def question_count(self):
        sql = "SELECT count(*) FROM question"
        (answer_count,) = self.execute(sql, return_row=True)
        return answer_count

    def learned_things_count(self):
        sql = "SELECT count(*) FROM (SELECT DISTINCT thing FROM answer) as foo"
        (answer_count,) = self.execute(sql, return_row=True)
        return answer_count

    def network_data(self, max_diff, min_links):
        sql = SIMILAR_THINGS.format(collected_answers=COLLECTED_ANSWERS,
                                    max_diff=max_diff, min_answers=10, min_links=min_links)
        things = {}
        links = []
        for thing_a, id_a, thing_b, id_b, dist, _, updated_recently in self.execute_and_get_rows(sql):
            if id_a not in things:
                things[id_a] = {'id': id_a, 'label': thing_a, 'updated_recently': updated_recently}
            if id_b not in things:
                things[id_b] = {'id': id_b, 'label': thing_b, 'updated_recently': False}
            things[id_a]['updated_recently'] |= updated_recently
            links.append({'from': id_a, 'to': id_b, 'length': dist + 1})
        return list(things.values()), links

    def matching_things(self, answers_so_far, wrong_guesses):
        answers = []
        for answer in answers_so_far:
            if answer.get('answer', None) == 'yes':
                yes, no = 1, 0
            elif answer.get('answer', None) == 'no':
                yes, no = 0, 1
            elif answer.get('answer', None) == 'sometimes':
                yes, no = 0.5, 0.5
            else:
                continue
            answers.append(f"(null,{answer['id']},{yes},{no})")
        if len(answers) < 1:
            return []

        things = []
        if wrong_guesses:
            filter_things = f"WHERE thing.id NOT IN ({','.join([str(x) for x in wrong_guesses])})"
        else:
            filter_things = ''
        sql = MATCHING_THINGS.format(collected_answers=COLLECTED_ANSWERS,
                                     values=','.join(answers),
                                     filter_things=filter_things)
        for thing_id, name, diff in self.execute_and_get_rows(sql):
            thing = {'id': thing_id, 'name': name, 'diff': diff}
            things.append(thing)

        return things

    def relevant_questions(self, relevant_things, used_questions):
        questions = []
        thing_ids = ','.join([str(x['id']) for x in relevant_things])
        question_ids = ','.join([str(x['id']) for x in used_questions])
        filterer = f"WHERE thing in ({thing_ids}) AND question NOT IN ({question_ids})"

        sql = RELEVANT_QUESTIONS.format(filterer=filterer)
        for question, question_id, _ in self.execute_and_get_rows(sql):
            questions.append({'id': question_id, 'question': question})
        return questions

    def record_guess_success(self, thing_id, guesses):
        sql = "INSERT INTO guess_success(thing, questions_needed) VALUES (%s,%s)"
        self.execute(sql, (thing_id, guesses))


if __name__ == '__main__':
    DB = Database({})
