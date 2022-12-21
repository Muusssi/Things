

CREATE TABLE thing (
    id serial PRIMARY KEY,
    name text UNIQUE
);

CREATE TABLE question (
    id serial PRIMARY KEY,
    question text UNIQUE,
    category text
);

CREATE TABLE answer (
    id serial PRIMARY KEY,
    thing int REFERENCES thing(id),
    question int REFERENCES question(id),
    answer text,
    timestamp timestamp default now()
);


