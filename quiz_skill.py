import logging

from flask import Flask, render_template

from flask_ask import Ask, statement, question, session

app = Flask(__name__)

ask = Ask(app, "/")

logging.getLogger("flask_ask").setLevel(logging.DEBUG)


@ask.launch
def new_quiz():
    welcome_msg = render_template('welcome')

    return question(welcome_msg)

@ask.intent("QuizMe", mapping={"course": "Class", "chapter": "Chapter"})
def quiz(course, chapter):
    message = render_template('verify', course=course, chapter=chapter)

    return statement(message)

if __name__ == '__main__':
    app.run(debug=True)