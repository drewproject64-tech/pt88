import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from telegram.error import NetworkError
from bot import ABOUT, DESCRIPTION, BUTTONS, build_application, clean_text, word_count, convert_case, respond, start, setup, USERNAME

class Tools(unittest.TestCase):
    def test_text_and_unicode(self):
        self.assertEqual(clean_text('  hello   world \n\n  next\t line '), 'hello world\nnext line')
        self.assertIn('Words: 3', word_count("Hello café don't"))
        self.assertEqual(convert_case('Straße'), 'UPPERCASE\nSTRASSE\n\nlowercase\nstraße')
        self.assertLessEqual(len(ABOUT), 120)
        self.assertLessEqual(len(DESCRIPTION), 512)
        self.assertEqual(len(build_application('123:ABC').handlers[0]), 6)

class Flows(unittest.IsolatedAsyncioTestCase):
    def context(self, text):
        self.message = SimpleNamespace(text=text, reply_text=AsyncMock(), reply_document=AsyncMock())
        return SimpleNamespace(effective_message=self.message), SimpleNamespace(user_data={})

    async def test_all_buttons_and_switch(self):
        update, context = self.context('hello')
        await respond(update, context)
        self.assertIn('Choose', self.message.reply_text.call_args.args[0])
        for button in BUTTONS:
            self.message.text = button
            await respond(update, context)
            self.assertEqual(context.user_data['tool'], button)
            self.message.text = '  Hello   world '
            await respond(update, context)
            self.assertTrue(self.message.reply_text.call_args.args[0])
        await start(update, context)
        self.assertEqual(context.user_data, {})

    async def test_long_unicode_file_and_limit(self):
        update, context = self.context('😀' * 2000)
        context.user_data['tool'] = BUTTONS[2]
        await respond(update, context)
        self.message.reply_document.assert_awaited_once()
        self.message.text = 'x' * 4001
        await respond(update, context)
        self.assertIn('4,000', self.message.reply_text.call_args.args[0])

    async def test_setup_recovers_transient_failure(self):
        bot = SimpleNamespace(username=USERNAME, set_my_name=AsyncMock(side_effect=[NetworkError('offline'), True]),
            set_my_short_description=AsyncMock(), set_my_description=AsyncMock(), set_my_commands=AsyncMock())
        from unittest.mock import patch
        with patch('bot.asyncio.sleep', new_callable=AsyncMock):
            await setup(SimpleNamespace(bot=bot))
        self.assertEqual(bot.set_my_name.await_count, 2)
        bot.set_my_description.assert_awaited_once_with(DESCRIPTION)
