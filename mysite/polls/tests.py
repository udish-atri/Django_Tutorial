import datetime

from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from .models import Question, Choice


class QuestionModelTests(TestCase):
    def test_was_published_recently_with_future_question(self):
        """
        was_published_recently() returns False for questions whose pub_date
        is in the future.
        """
        time = timezone.now() + datetime.timedelta(days=30)
        future_question = Question(pub_date=time)
        self.assertIs(future_question.was_published_recently(), False)

    def test_was_published_recently_with_old_question(self):
        """
        was_published_recently() returns False for questions whose pub_date
        is older than 1 day.
        """
        time = timezone.now() - datetime.timedelta(days=1, seconds=1)
        old_question = Question(pub_date=time)
        self.assertIs(old_question.was_published_recently(), False)

    def test_was_published_recently_with_recent_question(self):
        """
        was_published_recently() returns True for questions whose pub_date
        is within the last day.
        """
        time = timezone.now() - datetime.timedelta(hours=23, minutes=59, seconds=59)
        recent_question = Question(pub_date=time)
        self.assertIs(recent_question.was_published_recently(), True)

    def test_was_published_recently_with_exactly_now(self):
        """
        was_published_recently() returns True for questions published exactly now.
        """
        now_question = Question(pub_date=timezone.now())
        self.assertIs(now_question.was_published_recently(), True)

    def test_question_str_method(self):
        """
        __str__() returns the question text.
        """
        question = Question(question_text="What is your favorite color?")
        self.assertEqual(str(question), "What is your favorite color?")


class ChoiceModelTests(TestCase):
    def test_choice_str_method(self):
        """
        __str__() returns the choice text.
        """
        question = create_question(question_text="Test question", days=-1)
        choice = Choice(question=question, choice_text="Blue")
        self.assertEqual(str(choice), "Blue")

    def test_choice_default_votes(self):
        """
        New choices should have 0 votes by default.
        """
        question = create_question(question_text="Test question", days=-1)
        choice = Choice.objects.create(question=question, choice_text="Option A")
        self.assertEqual(choice.votes, 0)

    def test_choice_cascade_delete(self):
        """
        Deleting a question should delete all associated choices.
        """
        question = create_question(question_text="Test question", days=-1)
        choice1 = Choice.objects.create(question=question, choice_text="Choice 1")
        choice2 = Choice.objects.create(question=question, choice_text="Choice 2")

        question_id = question.id
        choice1_id = choice1.id
        choice2_id = choice2.id

        question.delete()

        self.assertFalse(Choice.objects.filter(id=choice1_id).exists())
        self.assertFalse(Choice.objects.filter(id=choice2_id).exists())


def create_question(question_text, days):
    """
    Create a question with the given `question_text` and published the
    given number of `days` offset to now (negative for questions published
    in the past, positive for questions that have yet to be published).
    """
    time = timezone.now() + datetime.timedelta(days=days)
    return Question.objects.create(question_text=question_text, pub_date=time)


def create_choice(question, choice_text, votes=0):
    """
    Create a choice for the given question with the specified text and votes.
    """
    return Choice.objects.create(
        question=question, choice_text=choice_text, votes=votes
    )


class QuestionIndexViewTests(TestCase):
    def test_no_questions(self):
        """
        If no questions exist, an appropriate message is displayed.
        """
        response = self.client.get(reverse("polls:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No polls are available.")
        self.assertQuerySetEqual(response.context["latest_question_list"], [])

    def test_past_question(self):
        """
        Questions with a pub_date in the past are displayed on the
        index page.
        """
        question = create_question(question_text="Past question.", days=-30)
        response = self.client.get(reverse("polls:index"))
        self.assertQuerySetEqual(
            response.context["latest_question_list"],
            [question],
        )

    def test_future_question(self):
        """
        Questions with a pub_date in the future aren't displayed on
        the index page.
        """
        create_question(question_text="Future question.", days=30)
        response = self.client.get(reverse("polls:index"))
        self.assertContains(response, "No polls are available.")
        self.assertQuerySetEqual(response.context["latest_question_list"], [])

    def test_future_question_and_past_question(self):
        """
        Even if both past and future questions exist, only past questions
        are displayed.
        """
        question = create_question(question_text="Past question.", days=-30)
        create_question(question_text="Future question.", days=30)
        response = self.client.get(reverse("polls:index"))
        self.assertQuerySetEqual(
            response.context["latest_question_list"],
            [question],
        )

    def test_two_past_questions(self):
        """
        The questions index page may display multiple questions.
        """
        question1 = create_question(question_text="Past question 1.", days=-30)
        question2 = create_question(question_text="Past question 2.", days=-5)
        response = self.client.get(reverse("polls:index"))
        self.assertQuerySetEqual(
            response.context["latest_question_list"],
            [question2, question1],
        )

    def test_only_five_most_recent_questions_displayed(self):
        """
        Only the 5 most recent questions are displayed on the index page.
        """
        questions = []
        for i in range(7):
            questions.append(
                create_question(question_text=f"Question {i}.", days=-(i + 1))
            )

        response = self.client.get(reverse("polls:index"))
        self.assertEqual(len(response.context["latest_question_list"]), 5)
        self.assertQuerySetEqual(
            response.context["latest_question_list"],
            questions[:5],
        )

    def test_questions_ordered_by_most_recent(self):
        """
        Questions are ordered from most recent to oldest.
        """
        q1 = create_question(question_text="Oldest.", days=-30)
        q2 = create_question(question_text="Middle.", days=-15)
        q3 = create_question(question_text="Newest.", days=-1)

        response = self.client.get(reverse("polls:index"))
        self.assertQuerySetEqual(
            response.context["latest_question_list"],
            [q3, q2, q1],
        )


class QuestionDetailViewTests(TestCase):
    def test_future_question(self):
        """
        The detail view of a question with a pub_date in the future
        returns a 404 not found.
        """
        future_question = create_question(question_text="Future question.", days=5)
        url = reverse("polls:detail", args=(future_question.id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_past_question(self):
        """
        The detail view of a question with a pub_date in the past
        displays the question's text.
        """
        past_question = create_question(question_text="Past Question.", days=-5)
        url = reverse("polls:detail", args=(past_question.id,))
        response = self.client.get(url)
        self.assertContains(response, past_question.question_text)

    def test_nonexistent_question(self):
        """
        The detail view returns 404 for a question that doesn't exist.
        """
        url = reverse("polls:detail", args=(99999,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_detail_view_displays_choices(self):
        """
        The detail view displays all choices for a question.
        """
        question = create_question(question_text="Test question?", days=-1)
        choice1 = create_choice(question, "Choice 1")
        choice2 = create_choice(question, "Choice 2")

        url = reverse("polls:detail", args=(question.id,))
        response = self.client.get(url)
        self.assertContains(response, choice1.choice_text)
        self.assertContains(response, choice2.choice_text)


class QuestionResultsViewTests(TestCase):
    def test_results_view_with_past_question(self):
        """
        The results view displays results for a past question.
        """
        question = create_question(question_text="Past question?", days=-5)
        choice1 = create_choice(question, "Choice 1", votes=5)
        choice2 = create_choice(question, "Choice 2", votes=3)

        url = reverse("polls:results", args=(question.id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, question.question_text)
        self.assertContains(response, choice1.choice_text)
        self.assertContains(response, choice2.choice_text)

    def test_results_view_displays_vote_counts(self):
        """
        The results view displays the vote count for each choice.
        """
        question = create_question(question_text="Test question?", days=-1)
        choice1 = create_choice(question, "Choice 1", votes=10)
        choice2 = create_choice(question, "Choice 2", votes=7)

        url = reverse("polls:results", args=(question.id,))
        response = self.client.get(url)
        self.assertContains(response, "10")
        self.assertContains(response, "7")

    def test_results_view_nonexistent_question(self):
        """
        The results view returns 404 for a question that doesn't exist.
        """
        url = reverse("polls:results", args=(99999,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class VoteViewTests(TestCase):
    def test_vote_increments_choice(self):
        """
        Voting on a choice increments its vote count by 1.
        """
        question = create_question(question_text="Test question?", days=-1)
        choice = create_choice(question, "Test choice")

        initial_votes = choice.votes
        url = reverse("polls:vote", args=(question.id,))
        response = self.client.post(url, {"choice": choice.id})

        choice.refresh_from_db()
        self.assertEqual(choice.votes, initial_votes + 1)

    def test_vote_redirects_to_results(self):
        """
        After voting, the user is redirected to the results page.
        """
        question = create_question(question_text="Test question?", days=-1)
        choice = create_choice(question, "Test choice")

        url = reverse("polls:vote", args=(question.id,))
        response = self.client.post(url, {"choice": choice.id})

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("polls:results", args=(question.id,)))

    def test_vote_without_choice_shows_error(self):
        """
        Voting without selecting a choice displays an error message.
        """
        question = create_question(question_text="Test question?", days=-1)
        create_choice(question, "Test choice")

        url = reverse("polls:vote", args=(question.id,))
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "didn&#x27;t select a choice")

    def test_vote_with_invalid_choice_shows_error(self):
        """
        Voting with an invalid choice ID displays an error message.
        """
        question = create_question(question_text="Test question?", days=-1)
        create_choice(question, "Test choice")

        url = reverse("polls:vote", args=(question.id,))
        response = self.client.post(url, {"choice": 99999})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "didn&#x27;t select a choice")

    def test_vote_on_nonexistent_question(self):
        """
        Voting on a nonexistent question returns 404.
        """
        url = reverse("polls:vote", args=(99999,))
        response = self.client.post(url, {"choice": 1})
        self.assertEqual(response.status_code, 404)

    def test_multiple_votes_increment_correctly(self):
        """
        Multiple votes on the same choice increment the count correctly.
        """
        question = create_question(question_text="Test question?", days=-1)
        choice = create_choice(question, "Test choice")

        url = reverse("polls:vote", args=(question.id,))

        for i in range(5):
            self.client.post(url, {"choice": choice.id})

        choice.refresh_from_db()
        self.assertEqual(choice.votes, 5)

    def test_votes_on_different_choices(self):
        """
        Votes are correctly attributed to different choices.
        """
        question = create_question(question_text="Test question?", days=-1)
        choice1 = create_choice(question, "Choice 1")
        choice2 = create_choice(question, "Choice 2")

        url = reverse("polls:vote", args=(question.id,))

        self.client.post(url, {"choice": choice1.id})
        self.client.post(url, {"choice": choice1.id})
        self.client.post(url, {"choice": choice2.id})

        choice1.refresh_from_db()
        choice2.refresh_from_db()

        self.assertEqual(choice1.votes, 2)
        self.assertEqual(choice2.votes, 1)
