import os
import sys
import time
import json
import pprint

from instabot_py import instabot

sys.path.append(os.path.join(sys.path[0], '../'))

COOKIE_FNAME = 'cookie.txt'


def _print_bot_last_state(bot):
    """Just pretty print the bot last state."""
    pprint.pprint(bot.last_response, indent=4)
    pprint.pprint(bot.last_response.headers, indent=4)
    pprint.pprint(bot.last_json, indent=4)
    

def _get_challenge_choices(last_json):
    """Analise the Json response and get possible choices."""
    choices = []

    # Checkpoint challenge
    if last_json.get('step_name', '') == 'select_verify_method':
        choices.append("Checkpoint challenge received")
        if 'phone_number' in last_json['step_data']:
            choices.append('0 - Phone')
        if 'email' in last_json['step_data']:
            choices.append('1 - Email')

    # Login alert challenge.
    # TODO: TESTS NEEDED
    if last_json.get('step_name', '') == 'delta_login_review':
        choices.append("Login attempt challenge received")
        choices.append('0 - It was me')
        choices.append('0 - It wasn\'t me')

    # If no choices found, use 1 as default.
    # TODO: TESTS NEEDED
    if not choices:
        choices.append(
            '"{}" challenge received'.format(
                last_json.get('step_name', 'Unknown')))
        choices.append('0 - Default')

    return choices


def _reset_challenge(_bot):
    """Is recommended to reset the challenge at the beginning."""
    challenge_url = _bot.last_json['challenge']['api_path'][1:]
    reset_url = challenge_url.replace('/challenge/', '/challenge/reset/')
    try:
        _bot.send_request(reset_url, login=True)
    except Exception as e:
        _bot.logger.error(e)
        return False
    return True


def _solve_checkpoint_challenge(_bot):
    # --- Start challenge
    time.sleep(3)
    challenge_url = _bot.last_json['challenge']['api_path'][1:]
    try:
        _bot.send_request(
            challenge_url, None, login=True, with_signature=False)
    except Exception as e:
        _bot.logger.error(e)
        return False

    # --- Choose and send back the choice
    # TODO: Sometimes ask to confirm phone or email. 
    # TODO: TESTS NEEDED
    time.sleep(3)
    choices = _get_challenge_choices(_bot.last_json)
    for choice in choices:
        print(choice)
    code = input('Insert choice:\n')
    data = json.dumps({'choice': code})
    try:
        _bot.send_request(challenge_url, data, login=True)
    except Exception as e:
        _bot.logger.error(e)
        return False

    # Print output for testing
    _print_bot_last_state(_bot)

    # --- Wait for the code, insert the code
    time.sleep(3)
    print("A code has been sent to the method selected, please check.")
    code = input('Insert code:\n')
    data = json.dumps({'security_code': code})
    try:
        _bot.send_request(challenge_url, data, login=True)
    except Exception as e:
        _bot.logger.error(e)
        return False

    # Print output for testing
    _print_bot_last_state(_bot)

    # --- If user logged in, save cookie, otherwise PASS
    worked = (
        ('logged_in_user' in _bot.last_json)
        and (_bot.last_json.get('action', '') == 'close')
        and (_bot.last_json.get('status', '') == 'ok'))
    if worked:
        # IMPORTANT, save the cookie at this step!
        _bot.save_cookie(COOKIE_FNAME)
        return True
    else:
        _bot.logger.error('Not possible to log in. Reset and try again')
        return False


bot = instabot

try:
    bot.login(use_cookie=False)
    bot.logger.info('User logged successfully, no Challenge required')
    exit()
except Exception as e:
    if bot.json('error_type', '') == 'checkpoint_challenge_required':
        print("Checkpoint_challenge found, attempting to solve...")
        success = _solve_checkpoint_challenge(bot)
        if success:
            bot.login(cookie_fname=COOKIE_FNAME)
    else:
        print("Unknown challenge found, share the next output to get support")
        _print_bot_last_state(bot)
