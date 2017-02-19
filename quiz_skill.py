import logging
import requests
import nlp as nlp

from flask import Flask, render_template

from flask_ask import Ask, statement, question, session

app = Flask(__name__)

ask = Ask(app, "/")

#logging.getLogger("flask_ask").setLevel(logging.DEBUG)

client_id = "2zMq3XjUTE"

@ask.launch
def new_quiz():
    welcome_msg = render_template("welcome")

    return question(welcome_msg)

@ask.intent("QuizCourseChapterIntent", mapping={"course_prefix": "CoursePrefix", "course_number": "CourseNumber", "course_letter": "CourseLetter", "chapter": "Chapter"})
def quizCourseChapterIntent(course_prefix, course_number, course_letter, chapter):
    course = course_prefix + " " + course_number
    if course_letter is not None:
        course += course_letter

    print course
    chapter_set = get_set(course, chapter)

    if chapter_set is None:
        return statement(render_template("error_finding_chapter_set", course=course, chapter=chapter))

    session.attributes["set"] = chapter_set
    message = render_template("check_ready", title=chapter_set["title"])

    print message

    return question(message)

@ask.intent("QuizCourseCategoryIntent", mapping={"course_prefix": "CoursePrefix", "course_number": "CourseNumber", "category": "Category"})
def quizCourseCategoryIntent(course_prefix, course_number, category):
    course = course_prefix + " " + course_number
    print course_number
    chapter_set = get_set(course, category)

    if chapter_set is None:
        return statement(render_template("error_finding_category_set", course=course, category=category))

    session.attributes["foreign_language_mode"] = True
    session.attributes["set"] = chapter_set
    message = render_template("check_ready", title=chapter_set["title"])

    print message

    return question(message)

@ask.intent("AMAZON.YesIntent")
def actually_start_quiz():
    session.attributes["current_term_index"] = -1
    return question(ask_next_term_message())

@ask.intent("AnswerIntent", mapping={"user_answer": "Answer"})
def process_answer_intent(user_answer):
    if user_answer is None:
        return question("I didn't get that. Could you repeat yourself?")

    current_term = get_current_term()
    correct_answer = current_term["definition"]
    correct = is_answer_correct(user_answer, correct_answer)

    print("User answered: " + user_answer)

    message = None
    if correct:
        message = "Correct!"
    else:
        message = render_template("incorrect_answer", term=current_term["term"], definition=current_term["definition"])

    if reached_end_of_terms():
        message += " You've reviewed all the terms."
        return statement(message)
    else:
        message += " Let's move on. "
        ask_next_message = ask_next_term_message()
        message += ask_next_message

        return question(message).reprompt("I didn't get that. " + ask_next_message)

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

    if session.attributes["foreign_language_mode"]:
        google_link = "https://translate.google.com/translate_tts?tl=es&amp;q=quiero&amp;client=tw-ob.mp3"
        message = "<speak><audio src=\"{}\"/></speak>".format(google_link)
    else:
        message = prefix + render_template("ask_definition", term=current_term)

    return message

def quizlet_get(url, params={}):
    params["client_id"] = client_id
    return requests.get(url, params)

def get_set_from_group(course, keyword, group_id):
    r = quizlet_get("https://api.quizlet.com/2.0/groups/{}/sets".format(group_id))
    keyword = keyword.lower()
    for group_set in r.json():
        title = group_set["title"].lower()
        if title is not None:
            print title
        if title is not None and keyword in title:
            return group_set

    return None

def get_set(course, keyword):
    params = {
        "q": course
    }
    r = quizlet_get("https://api.quizlet.com/2.0/search/groups", params=params)
    flashcard_set = None
    for group in r.json()["classes"]:
        if "school" in group and "name" in group["school"] and "Stanford" in group["school"]["name"]:
            group_id = group["id"]
            flashcard_set = get_set_from_group(course, keyword, group_id)

            if flashcard_set is not None:
                break

    if flashcard_set is None:
        print("ERROR: Could not find set for course: " + course + " and keyword: " + keyword)
        return

    return flashcard_set

if __name__ == "__main__":
    app.run(debug=True)
