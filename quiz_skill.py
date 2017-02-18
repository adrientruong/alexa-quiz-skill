import logging
import requests
import nlp as nlp

from flask import Flask, render_template

from flask_ask import Ask, statement, question, session

app = Flask(__name__)

ask = Ask(app, "/")

logging.getLogger("flask_ask").setLevel(logging.DEBUG)

client_id = "2zMq3XjUTE"

@ask.launch
def new_quiz():
    welcome_msg = render_template("welcome")

    return question(welcome_msg)

@ask.intent("QuizMe", mapping={"course": "Class", "chapter": "Chapter"})
def quiz(course, chapter):
    chapter_set = get_set(course, chapter)
    session.attributes["set"] = chapter_set
    message = render_template("check_ready", title=chapter_set["title"])

    return question(message)

@ask.intent("AMAZON.YesIntent")
def actually_start_quiz():
    session.attributes["current_term_index"] = -1
    return question(ask_next_term_message())

@ask.intent("AnswerIntent", mapping={"user_answer": "Answer"})
def process_answer_intent(user_answer):
    current_term = get_current_term()
    correct_answer = current_term["definition"]
    correct = is_answer_correct(user_answer, correct_answer)

    message = None
    if correct:
        message = "Correct!"
        if reached_end_of_terms():
            message += " You've reviewed all the terms."
        else:
            message += " Let's move on. "
            message += ask_next_term_message()
    else:
        message = render_template("incorrect_answer", term=current_term["term"], definition=current_term["definition"])

    return question(message)

def reached_end_of_terms():
    chapter_set = session.attributes["set"]
    current_index = session.attributes["current_term_index"]
    reached = len(chapter_set["terms"]) == current_index + 1
    return reached

def is_answer_correct(user_answer, correct_answer):
    return nlp.isCorrect(correct_answer, user_answer) # Order matters, this is better than nlp.isCorrect(user_answer, correct_answer)

def get_current_term():
    current_index = session.attributes["current_term_index"]
    chapter_set = session.attributes["set"]
    term = chapter_set["terms"][current_index]

    return term

def ask_next_term_message():
    current_index = session.attributes["current_term_index"]
    current_index += 1
    session.attributes["current_term_index"] = current_index

    return ask_term_message(current_index)

def ask_term_message(index, prefix=""):
    chapter_set = session.attributes["set"]
    current_term = chapter_set["terms"][index]["term"]
    if len(prefix) != 0:
        prefix += " "
    message = prefix + render_template("ask_definition", term=current_term)

    return message

def quizlet_get(url, params={}):
    params["client_id"] = client_id
    return requests.get(url, params)

def get_set(course, chapter):
    params = {
        "q": course
    }
    r = quizlet_get("https://api.quizlet.com/2.0/search/groups", params=params)
    course_groups = []
    for group in r.json()["classes"]:
        if "Stanford" in group["school"]["name"]:
            course_groups.append(group)

    if len(course_groups) == 0:
        print "uh oh spaghettio. could not find group for course"
        return

    chapter_set = None
    for course_group in course_groups:

        group_id = course_group["id"]
        r = quizlet_get("https://api.quizlet.com/2.0/groups/{}/sets".format(group_id))

        for group_set in r.json():
            if chapter in group_set["title"]:
                chapter_set = group_set
                break

        if chapter_set is not None:
            break

    if chapter_set is None:
        print "uh oh spaghettio. could not find set for chapter"

    return chapter_set

if __name__ == "__main__":
    app.run(debug=True)
