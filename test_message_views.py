"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py

import os
from unittest import TestCase

from models import db, connect_db, Message, User

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"

# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        user = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)

        db.session.add(user)
        db.session.commit()

        self.user_id = user.id

        message = Message(text='Test Message', 
                            user_id=user.id)
        
        db.session.add(message)
        db.session.commit()

        self.message_id = message.id

    def test_add_message(self):
        """Can user add a message?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.user_id

            # Now, that session setting is saved, we can have
            # the rest of ours test

            resp = c.post("/messages/new", data={"text": "Hello"})

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            msg = Message.query.get(self.message_id + 1)
            self.assertEqual(msg.text, "Hello")

    def test_delete_message(self):
        """Can user delete their own message?"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.user_id

            resp = c.post(f"/messages/{self.message_id}/delete")

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            msg = Message.query.first()
            self.assertEqual(msg, None)

    def test_add_message_logged_out(self):
        with self.client as c:
            resp = c.post("/messages/new", data={"text": "Hello"}, follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))

    def test_delete_message_logged_out(self):
        """Is user prohibited from deleting message when logged out?"""

        with self.client as c:
            resp = c.post(f"/messages/{self.message_id}/delete")

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            msgs = Message.query.all()
            self.assertEqual(len(msgs), 1)

    def test_add_message_as_other_user(self):
        """Is user prohibited from adding a message as different user?"""

        user2 = User.signup(username="testuser2",
                                    email="test2@test.com",
                                    password="testuser2",
                                    image_url=None)

        user2.id = 647

        db.session.add(user2)
        db.session.commit()
        
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.user_id
            #user from set up attempting to send message as user2 
            resp = c.post("/messages/new", data={"text": "New", 
                                                "user_id": 647})

            self.assertEqual(resp.status_code, 302)

            msg = Message.query.one()
            self.assertEqual(msg.text, "Hello")

    def test_delete_message_as_other_user(self):
        """Is user prohibited from deleting a message of different user?"""
        #user 2 to attempt deleting user message from set up
        user2 = User.signup(username="testuser2",
                                    email="test2@test.com",
                                    password="testuser2",
                                    image_url=None)
        user2.id = 123

        db.session.add(user2)
        db.session.commit()
        #login as user 2
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = user2.id
            #attempt to delete user 1 (from set up) message
            resp = c.post(f"/messages/{self.message_id}/delete")

            self.assertEqual(resp.status_code, 302)

            msgs = Message.query.all()
            self.assertEqual(len(msgs), 1)
